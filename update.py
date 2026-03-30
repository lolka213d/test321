import bpy
import os
import sys
import requests
import zipfile
import subprocess
from threading import Thread
import shutil
import asyncio
from . import glob_vars
from test321 import i18n, addon_version


# Centralized update URL (use the release zip URL configured in glob_vars)
UPDATE_URL = glob_vars.rbx_update_test_down_link


# Global variables to track the state of the operator
download_progress = 0
operator_state = "IDLE"  # States: IDLE, DOWNLOADING, INSTALLING, FINISHED, ERROR
error_message = ""
current_operator = None



def restart_blender(self):
    import subprocess, sys
    blender_exe = sys.argv[0]
    subprocess.Popen([blender_exe])
    bpy.ops.wm.quit_blender()


# This asynchronous method is invoked as a separate coroutine from the main thread
async def oauth_logout(context):
    """oAuth Logout"""
    need_restart_blender = False
    from oauth.lib.oauth2_client import RbxOAuth2Client
    window_manager = context.window_manager
    rbx = window_manager.rbx
    oauth2_client = RbxOAuth2Client(rbx)

    if rbx.is_logged_in:
        await oauth2_client.logout()
        need_restart_blender = True
    print("Successfully logged out for update RBX Toolbox")
    return need_restart_blender





class RBX_INSTALL_UPDATE(bpy.types.Operator):
    bl_idname = "wm.install_update"
    bl_label = i18n.t('install_update')
    _timer = None
    restart_only: bpy.props.BoolProperty(default=False) # type: ignore

    # Add a property for the progress bar
    progress: bpy.props.FloatProperty(
        name="Progress",
        subtype="PERCENTAGE",
        soft_min=0,
        soft_max=100,
        precision=1,
    ) # type: ignore


    def execute(self, context):
        global operator_state, download_progress, error_message, current_operator

        # Only call restart Blender
        if self.restart_only:
            self.restart_blender()
            return {'FINISHED'}
        


        # Start the download in a separate thread
        if operator_state == "IDLE":

            # Run async function from sync context and Logout
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            need_restart_blender = loop.run_until_complete(oauth_logout(context))
            if need_restart_blender:
                glob_vars.need_restart_blender = need_restart_blender
                return {'FINISHED'}
            
            else:
                current_operator = self  # Store the operator instance
                operator_state = "DOWNLOADING"
                download_progress = 0
                error_message = ""
                self.download_thread = Thread(target=self.download_file)
                self.download_thread.start()
                context.window_manager.modal_handler_add(self)
                self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
                return {'RUNNING_MODAL'}
        
        ### This is after addon installed and the button changes to Restart Blender
        elif operator_state == "FINISHED":
            # Restart Blender
            blender_exe = sys.argv[0]  # Get the Blender executable path
            subprocess.Popen([blender_exe])
            bpy.ops.wm.quit_blender()
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Operator is already running.")
            return {'CANCELLED'}



    def download_file(self):
        """Download and install update from GitHub"""
        global operator_state, download_progress, error_message

        try:
            # Get the addon's directory
            addon_path = os.path.dirname(os.path.abspath(__file__))
            download_path = os.path.join(addon_path, "update.zip")

            # Simulate a file download
            print("Downloading update...")
            # Use the latest URL from glob_vars at download time (fix stale module-level constant)
            url = getattr(glob_vars, 'rbx_update_test_down_link', None) or UPDATE_URL
            print("Update URL:", url)
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an error for bad status codes
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        download_progress = (downloaded_size / total_size) * 100

                        # Update the progress property
                        self.progress = download_progress


            # Simulate installation after download
            operator_state = "INSTALLING"
            self.install_addon(download_path, addon_path)

        except Exception as e:
            operator_state = "ERROR"
            error_message = str(e)
            print("Download ERROR: ", error_message)



    def install_addon(self, download_path, addon_path):
        """Download and install update from GitHub"""
        global operator_state, error_message

        try:
            print("Simulate installing")
            #Delete old add-on files (except update.zip)
            for filename in os.listdir(addon_path):
                file_path = os.path.join(addon_path, filename)
                if os.path.isfile(file_path) and filename != "update.zip":
                    os.remove(file_path)
                elif os.path.isdir(file_path) and filename != "rig_aepbr":
                    shutil.rmtree(file_path)

            # Extract ZIP
            #normpath - Normalizes the path (removes trailing / or \ if present)
            #dirname - Extracts the parent directory
            parent_path = os.path.dirname(os.path.normpath(addon_path))
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(parent_path)

            # Cleanup update.zip
            os.remove(download_path)

            # Mark installation as complete
            print("Update Installed! Successfully. Please restart Blender")
            operator_state = "FINISHED"

        except Exception as e:
            operator_state = "ERROR"
            error_message = str(e)
            print("Update ERROR: ", error_message)



    def modal(self, context, event):
        global operator_state, error_message, download_progress
        scene = context.scene


        if event.type == 'TIMER':
            # Redraw all regions of the UI type where your panel resides (e.g., 'VIEW_3D')
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':  # Adjust if your panel is in a different area
                    area.tag_redraw()
        
        
        if operator_state == "ERROR":
            self.report({'ERROR'}, f"Error: {error_message}")
            return {'FINISHED'}

        if operator_state == "FINISHED":
            self.report({'INFO'}, "Installation finished. Please restart Blender.")
            return {'FINISHED'}

        # Continue running
        return {'PASS_THROUGH'}
    

    ### This is after addon installed and the button changes to Restart Blender
    def restart_blender(self):
        # Restart Blender
        blender_exe = sys.argv[0]  # Get the Blender executable path
        subprocess.Popen([blender_exe])
        bpy.ops.wm.quit_blender()
        return {'FINISHED'}



class RBX_CHECK_UPDATE(bpy.types.Operator):
    """Check GitHub releases for an update and (optionally) start install."""
    bl_idname = "wm.check_update"
    bl_label = i18n.t('check_for_updates')

    latest_tag: bpy.props.StringProperty(default="")
    latest_url: bpy.props.StringProperty(default="")

    def invoke(self, context, event):
        try:
            import urllib.parse
            url = glob_vars.rbx_update_test_down_link
            parsed = urllib.parse.urlparse(url)
            parts = parsed.path.strip('/').split('/')
            if len(parts) < 2:
                self.report({'WARNING'}, i18n.t('no_internet_connection_skipping_rbx_tool'))
                return {'FINISHED'}
            owner, repo = parts[0], parts[1]
            api_url = f'https://api.github.com/repos/{owner}/{repo}/releases/latest'
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            tag = data.get('tag_name') or data.get('name') or ''
            assets = data.get('assets', [])
            asset_url = None
            for a in assets:
                name = a.get('name', '')
                if name.lower().endswith('.zip'):
                    if name.lower().startswith(repo.lower()) or name.lower() == f'{repo}.zip':
                        asset_url = a.get('browser_download_url')
                        break
                    if not asset_url:
                        asset_url = a.get('browser_download_url')
            if not asset_url:
                asset_url = data.get('zipball_url')

            self.latest_tag = tag
            self.latest_url = asset_url

            def norm(t):
                if not t:
                    return ''
                t = str(t)
                return t.lstrip('v').lstrip('.')

            if norm(tag) and norm(tag) != norm(addon_version):
                return context.window_manager.invoke_confirm(self, event)
            else:
                self.report({'INFO'}, i18n.t('no_update_found'))
                return {'FINISHED'}
        except requests.exceptions.RequestException:
            self.report({'WARNING'}, i18n.t('no_internet_connection_skipping_rbx_tool'))
            return {'FINISHED'}
        except Exception as e:
            self.report({'WARNING'}, f'Update check failed: {e}')
            return {'FINISHED'}

    def execute(self, context):
        if self.latest_url:
            glob_vars.lts_ver = self.latest_tag if self.latest_tag else None
            glob_vars.rbx_update_test_down_link = self.latest_url
            # Start the existing install operator
            bpy.ops.wm.install_update()
            return {'FINISHED'}
        self.report({'INFO'}, i18n.t('no_update_found'))
        return {'FINISHED'}


