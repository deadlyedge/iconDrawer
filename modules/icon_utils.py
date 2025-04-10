import logging
import ctypes
from ctypes import wintypes
from typing import Optional
from PySide6.QtGui import QIcon, QPixmap, QImage # Import QImage
import os # Need os for path checks

# Import the refactored components
from .icon_provider import DefaultIconProvider
from .icon_validators import validate_path
from .icon_dispatcher import IconDispatcher

# --- Global Variables (Lazy Initialized) ---
_icon_provider: Optional[DefaultIconProvider] = None
_icon_dispatcher: Optional[IconDispatcher] = None
_unknown_icon: Optional[QIcon] = None
_initialized = False

# --- Initialization Function ---
def _initialize_icon_components():
    """Initializes the icon components only when needed."""
    global _icon_provider, _icon_dispatcher, _unknown_icon, _initialized
    if _initialized:
        return

    try:
        _icon_provider = DefaultIconProvider()
        _icon_dispatcher = IconDispatcher(_icon_provider)
        _unknown_icon = _icon_provider.get_unknown_icon()
        _initialized = True
        logging.debug("Icon components initialized successfully.")
    except Exception as e:
        logging.critical(f"Failed to initialize icon components: {e}", exc_info=True)
        # Ensure fallbacks are set even on error
        _icon_provider = None
        _icon_dispatcher = None
        _unknown_icon = QIcon() # Basic empty icon
        _initialized = True # Mark as initialized to prevent retries


# --- Windows API Specific Icon Retrieval (New Method) ---
# Only attempt on Windows
_is_windows = os.name == 'nt' # More reliable check for Windows

if _is_windows:
    try:
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        # Define SHGetFileInfoW constants and structure
        SHGFI_ICON = 0x000000100
        SHGFI_USEFILEATTRIBUTES = 0x000000010
        FILE_ATTRIBUTE_NORMAL = 0x0080
        FILE_ATTRIBUTE_DIRECTORY = 0x0010

        class SHFILEINFO(ctypes.Structure):
            _fields_ = [
                ('hIcon', wintypes.HICON),
                ('iIcon', wintypes.INT),
                ('dwAttributes', wintypes.DWORD),
                ('szDisplayName', wintypes.WCHAR * 260),
                ('szTypeName', wintypes.WCHAR * 80)
            ]

        # Define GetIconInfo constants and structure
        class ICONINFO(ctypes.Structure):
            _fields_ = [
                ('fIcon', wintypes.BOOL),
                ('xHotspot', wintypes.DWORD),
                ('yHotspot', wintypes.DWORD),
                ('hbmMask', wintypes.HBITMAP),
                ('hbmColor', wintypes.HBITMAP)
            ]

        def _get_icon_via_windows_api(path: str) -> Optional[QIcon]:
            """
            Attempts to get an icon using the Windows SHGetFileInfoW API.
            Includes resource cleanup. Returns None if not on Windows or on error.
            """
            if not _is_windows: # Double check, though outer block handles this
                return None

            info = SHFILEINFO()
            # Use os.path.isdir for a more robust check
            # Need absolute path for isdir and SHGetFileInfoW
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path): # SHGetFileInfo might work even if path doesn't exist for some types, but good to check
                 # logging.debug(f"Path does not exist: {abs_path}")
                 return None

            is_dir = os.path.isdir(abs_path)
            file_attributes = FILE_ATTRIBUTE_DIRECTORY if is_dir else FILE_ATTRIBUTE_NORMAL
            flags = SHGFI_ICON | SHGFI_USEFILEATTRIBUTES

            result = shell32.SHGetFileInfoW(
                abs_path,
                file_attributes,
                ctypes.byref(info),
                ctypes.sizeof(info),
                flags
            )

            icon_handle = info.hIcon
            q_icon = None

            # Check if SHGetFileInfoW succeeded and returned a valid icon handle
            if result != 0 and icon_handle:
                icon_info = ICONINFO()
                get_icon_info_success = user32.GetIconInfo(icon_handle, ctypes.byref(icon_info))
                # Store handles for cleanup *before* potential errors
                color_handle_to_delete = icon_info.hbmColor if get_icon_info_success else None
                mask_handle_to_delete = icon_info.hbmMask if get_icon_info_success else None

                if get_icon_info_success:
                    color_pixmap = None
                    if color_handle_to_delete:
                        # Create QImage first, then QPixmap
                        qimage = QImage.fromHBITMAP(color_handle_to_delete)
                        if not qimage.isNull():
                            color_pixmap = QPixmap.fromImage(qimage)
                        if color_pixmap is None or color_pixmap.isNull(): # Check if conversion failed
                             color_pixmap = None
                             # logging.debug(f"QImage/QPixmap conversion failed for color handle: {color_handle_to_delete}")


                    if color_pixmap:
                        q_icon = QIcon(color_pixmap)
                        # Mask handling is complex and often not needed for basic icons, skip for now
                        # if mask_handle_to_delete:
                        #    mask_pixmap = QPixmap.fromWinHBITMAP(mask_handle_to_delete)
                        #    if mask_pixmap and not mask_pixmap.isNull():
                        #       color_pixmap.setMask(mask_pixmap.mask()) # Apply mask
                        #       q_icon = QIcon(color_pixmap) # Update icon with masked pixmap
                        #    if mask_handle_to_delete: gdi32.DeleteObject(mask_handle_to_delete) # Clean up mask handle

                # --- Cleanup ---
                try:
                    # Delete HBITMAPs only if they were successfully retrieved and non-zero
                    if color_handle_to_delete:
                        # logging.debug(f"Attempting to delete color HBITMAP: {color_handle_to_delete}")
                        if not gdi32.DeleteObject(wintypes.HBITMAP(color_handle_to_delete)):
                            logging.warning(f"Failed to delete color HBITMAP: {color_handle_to_delete}")
                    if mask_handle_to_delete:
                        # logging.debug(f"Attempting to delete mask HBITMAP: {mask_handle_to_delete}")
                        if not gdi32.DeleteObject(wintypes.HBITMAP(mask_handle_to_delete)):
                             logging.warning(f"Failed to delete mask HBITMAP: {mask_handle_to_delete}")
                except (OverflowError, ctypes.ArgumentError) as delete_error:
                    logging.warning(f"Error during GDI object deletion: {delete_error}. Handles: color={color_handle_to_delete}, mask={mask_handle_to_delete}")

                # Destroy the HICON regardless of GetIconInfo success, as SHGetFileInfoW gave it to us
                # It's crucial to destroy the HICON handle from SHGetFileInfoW
                try:
                    # logging.debug(f"Attempting to destroy HICON: {icon_handle}")
                    if not user32.DestroyIcon(wintypes.HICON(icon_handle)):
                        logging.warning(f"Failed to destroy HICON: {icon_handle}")
                except (OverflowError, ctypes.ArgumentError) as destroy_error:
                     logging.warning(f"Error destroying HICON: {destroy_error}. Handle: {icon_handle}")
            # No else needed for destroying icon_handle here, it's done above if valid

            return q_icon
    except ImportError:
         logging.warning("ctypes or wintypes not available. Windows API icon retrieval disabled.")
         _is_windows = False # Disable if imports fail
         def _get_icon_via_windows_api(path: str) -> Optional[QIcon]: return None
    except AttributeError:
         logging.warning("Required Windows API functions not found. Windows API icon retrieval disabled.")
         _is_windows = False # Disable if functions are missing
         def _get_icon_via_windows_api(path: str) -> Optional[QIcon]: return None
    except Exception as e:
        logging.error(f"Unexpected error setting up Windows API for icons: {e}", exc_info=True)
        _is_windows = False # Disable on unexpected error during setup
        # Define a dummy function if setup fails to avoid NameError later
        def _get_icon_via_windows_api(path: str) -> Optional[QIcon]:
            return None
else:
    # Define a dummy function if not on Windows
    def _get_icon_via_windows_api(path: str) -> Optional[QIcon]:
        return None

# --- Public API ---
def get_icon_for_path(full_path: str) -> QIcon:
    """
    Gets the appropriate QIcon for a given file system path using a
    refactored validator/dispatcher/worker pattern.

    Args:
        full_path: The absolute path to the file or directory.

    Returns:
        The most appropriate QIcon found, or a default unknown icon if
        the path is invalid or no specific icon could be determined.
    """
    # 1. Try the new Windows API method first (if on Windows and initialized)
    if _is_windows:
        try:
            win_icon = _get_icon_via_windows_api(full_path)
            if win_icon and not win_icon.isNull(): # Check if icon is valid
                # logging.debug(f"Windows API returned icon for '{full_path}'")
                return win_icon
            # else:
                # logging.debug(f"Windows API did not return a valid icon for '{full_path}', falling back.")
        except Exception as e:
            # Log error and fall through to the original method
            logging.error(f"Error calling _get_icon_via_windows_api for '{full_path}': {e}", exc_info=True)

    # 2. Ensure components are initialized (happens only once, or if WinAPI failed/returned nothing)
    _initialize_icon_components()

    # 3. Use the initialized components (or fallbacks if init failed)
    # Add checks for None in case initialization failed critically
    local_unknown_icon = _unknown_icon if _unknown_icon is not None else QIcon()
    local_icon_dispatcher = _icon_dispatcher

    if not local_icon_dispatcher:
        logging.error("Icon dispatcher not available, returning fallback icon.")
        return local_unknown_icon

    # 1. Validate the path
    validated_path_info = validate_path(full_path)
    if not validated_path_info:
        # logging.debug(f"Path validation failed for '{full_path}', returning fallback icon.")
        return local_unknown_icon # Return fallback icon if path is invalid

    # 2. Dispatch to the appropriate worker
    try:
        icon = local_icon_dispatcher.dispatch(validated_path_info)
        # logging.debug(f"Dispatcher returned icon for '{full_path}': {icon is not None}")

        # 3. Handle final fallback if dispatcher didn't find anything
        return icon if icon else local_unknown_icon

    except Exception as e:
        logging.error(
            f"Error during icon dispatch for path '{full_path}': {e}",
            exc_info=True # Include stack trace in log
        )
        return local_unknown_icon # Return fallback icon on unexpected error

# --- Cleanup ---
# (No explicit cleanup needed for these components in this structure)
