import os
from test321 import glob_vars


### Debug prints
DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs) if DEBUG else None


def resolve_content_uri(value):
    """Extract a URI string from an rbxm_reader Content property value.
    Content properties in the new reader return dicts like:
      {"type": "Uri", "uri": "rbxassetid://123"}
      {"type": "None"}
    Also handles plain strings (backwards compat) and None.
    Returns the URI string, or empty string if not available.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        if value.get("type") == "Uri":
            return value.get("uri", "")
        return ""
    # Plain string (backwards compat or already resolved)
    return str(value)


def replace_restricted_char(s: str = None):
    """Replace restricted characters in string with underscores"""
    if s is None:
        return
    restricted_chars = '\/*?:"<>|.,'
    replace_map = dict((ord(char), '_') for char in restricted_chars)
    new_str = s.translate(replace_map)
    return new_str


def strip_rbxassetid(asset_str):
    """Removes the 'rbxassetid://' prefix if present or extracts ID after '='"""
    asset_str = str(asset_str)
    prefix = "rbxassetid://"
    if asset_str.startswith(prefix):
        return asset_str[len(prefix):]
    else:
        # fallback: take last part after '=' if present
        asset_str = asset_str.split("=")[-1]
    return asset_str


async def renew_token(context):
    """Refreshes Auth Token (async helper)"""
    from oauth.lib.oauth2_client import RbxOAuth2Client
    window_manager = context.window_manager
    rbx = window_manager.rbx
    oauth2_client = RbxOAuth2Client(rbx)
    await oauth2_client.refresh_login_if_needed()
    access_token = oauth2_client.token_data.get("access_token")
    dprint("Auth Token refresh after: ", oauth2_client.token_data.get("refresh_after"))
    return access_token


def get_cdn_url(hash):
    i = 31
    for char in hash:
        i ^= ord(char)
    return f"https://t{i%8}.rbxcdn.com/{hash}"


def create_and_open_folders(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    try:
        os.startfile(folder)
    except Exception:
        pass
    return


def cleanup_tmp_files(filenames: list, extension: str, folder_path: str = None):
    """
    Deletes files from folder_path whose names match the list, with the given extension.
    If folder_path is not provided, defaults to tmp_rbxm inside addon import folder.
    """
    if folder_path is None:
        folder_path = os.path.join(glob_vars.addon_path, glob_vars.rbx_import_main_folder, 'tmp_rbxm')
    # make sure extension starts with "."
    if not extension.startswith("."):
        extension = "." + extension

    missing = []
    for name in filenames:
        file_path = os.path.join(folder_path, str(name) + extension)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        else:
            missing.append(file_path)

    return


def save_to_file(file, data):
    """Saving binary data to file."""
    rbx_imp_error = None
    try:
        with open(file, "wb") as f:
            f.write(data)
    except Exception as e:
        rbx_imp_error = f"Error saving file. {e}"
        glob_vars.rbx_imp_error = rbx_imp_error
    return rbx_imp_error


def item_field_extract_id(rbx_item_field_entry):
    dprint("rbx_item_field_entry: ", rbx_item_field_entry)
    rbx_asset_id = None
    rbx_imp_error = None

    rbx_cat_url = "https://www.roblox.com/catalog/"
    rbx_bndl_url = "https://www.roblox.com/bundles/"
    rbx_store_url = "https://create.roblox.com/store/asset/"
    rbx_games_url = "https://www.roblox.com/games/"
    
    # Clean up input
    if isinstance(rbx_item_field_entry, str) and rbx_item_field_entry.startswith("http://"):
        rbx_item_field_entry = rbx_item_field_entry.replace("http://", "https://")

    if rbx_cat_url in rbx_item_field_entry:
        rbx_asset_id = rbx_item_field_entry.replace(rbx_cat_url, "")
        rbx_asset_id = rbx_asset_id.split("/")[0]
    elif rbx_bndl_url in rbx_item_field_entry:
        rbx_asset_id = rbx_item_field_entry.replace(rbx_bndl_url, "")
        rbx_asset_id = rbx_asset_id.split("/")[0]
    elif rbx_store_url in rbx_item_field_entry:
        # Handle: https://create.roblox.com/store/asset/17253530672/rainbow-obby
        rbx_asset_id = rbx_item_field_entry.replace(rbx_store_url, "")
        rbx_asset_id = rbx_asset_id.split("/")[0]
        rbx_asset_id = rbx_asset_id.split("?")[0]  # Strip query params
    elif rbx_games_url in rbx_item_field_entry:
        rbx_asset_id = rbx_item_field_entry.replace(rbx_games_url, "")
        rbx_asset_id = rbx_asset_id.split("/")[0]
        rbx_asset_id = rbx_asset_id.split("?")[0]  # Strip query params
    elif isinstance(rbx_item_field_entry, str) and rbx_item_field_entry.isdigit():
        rbx_asset_id = rbx_item_field_entry
    else:
        rbx_imp_error = "Error: Invalid item URL or ID"
        glob_vars.rbx_imp_error = rbx_imp_error

    if rbx_asset_id and not str(rbx_asset_id).isdigit():
        rbx_asset_id = None
        rbx_imp_error = "Error: extracted ID is not a number"
        glob_vars.rbx_imp_error = rbx_imp_error

    return rbx_asset_id, rbx_imp_error
