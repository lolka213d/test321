import traceback
import bpy
import os
import glob
import bmesh
from test321 import glob_vars
from glob_vars import addon_path
from . import menu_pie
from test321 import update
from test321 import update_aepbr
from test321 import props
from test321 import addon_version, addon_label
from test321 import i18n
from bpy_extras.io_utils import ImportHelper

def get_aepbr_cur_ver():
    rbx_aepbr_fldr_path = os.path.join(addon_path, glob_vars.rbx_aepbr_fldr)
    try:
        rbx_aepbr_blend = os.listdir(rbx_aepbr_fldr_path)[0]
        rbx_aepbr_filename = rbx_aepbr_blend.split('.bl')[0]
        aepbr_cur_ver = rbx_aepbr_filename.split('v.')[1]
    except:
        aepbr_cur_ver = '0'
    return aepbr_cur_ver


def _get_human_model_candidates(scene):
    candidates = []
    for obj in scene.objects:
        if obj.type != "ARMATURE":
            continue
        if not obj.visible_get():
            continue
        if any(child.type == "MESH" for child in obj.children_recursive):
            candidates.append(obj)
    return candidates

class RBX_OT_terms_of_use(bpy.types.Operator):
    """Terms of Use for Import (Beta)"""
    bl_idname = 'object.rbx_terms_of_use'
    bl_label = i18n.t('terms_of_use')
    bl_options = {'REGISTER', 'INTERNAL'}
    action: bpy.props.StringProperty(default='SHOW')

    def invoke(self, context, event):
        if self.action == 'ACCEPT':
            prefs = context.preferences.addons['test321'].preferences
            prefs.accepted_terms_of_use = True
            bpy.ops.wm.save_userpref()
            self.report({'INFO'}, i18n.t('terms_of_use_accepted'))
            return {'FINISHED'}
        elif self.action == 'DECLINE':
            self.report({'WARNING'}, i18n.t('terms_of_use_declined'))
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text=i18n.t('agreement'), icon='BOOKMARKS')
        col = box.column(align=True)
        col.label(text=i18n.t('by_using_this_tool_you_agree_that_anythi'))
        col.label(text=i18n.t('download_is_strictly_for_your_personal_u'))
        col.label(text=i18n.t('and_research_purposes_only_you_hereby_ma'))
        col.label(text=i18n.t('completely_serious_legallybindinginspiri'))
        col.label(text=i18n.t('promise_not_to_reupload_redistribute_res'))
        col.label(text=i18n.t('the_downloaded_content_as_your_own'))
        layout.separator()
        box = layout.box()
        box.alert = True
        box.label(text=i18n.t('warning'), icon='ERROR')
        col = box.column(align=True)
        col.label(text=i18n.t('roblox_is_actively_tracking_asset_access'))
        col.label(text=i18n.t('activity_this_includes_hashes_device_inf'))
        col.label(text=i18n.t('addresses_and_usage_patterns_they_can_technically'))
        col.label(text=i18n.t('pinpoint_the_source_of_misuse_abuse_of_this_tool_m'))
        col.label(text=i18n.t('result_in_account_suspension_termination_or_furthe'))
        col.label(text=i18n.t('action_use_responsibly'))

    def execute(self, context):
        prefs = context.preferences.addons['test321'].preferences
        prefs.accepted_terms_of_use = True
        bpy.ops.wm.save_userpref()
        self.report({'INFO'}, i18n.t('terms_of_use_accepted'))
        return {'FINISHED'}


class RBX_OT_upload_skin(bpy.types.Operator, ImportHelper):
    """Load a local image and apply it as a skin texture to selected mesh(es)"""
    bl_idname = 'object.rbx_upload_skin'
    bl_label = i18n.t('upload_skin')
    filename_ext = "*.png;*.jpg;*.jpeg"
    filter_glob: bpy.props.StringProperty(default='*.png;*.jpg;*.jpeg', options={'HIDDEN'})

    def execute(self, context):
        filepath = getattr(self, 'filepath', None)
        if not filepath:
            self.report({'ERROR'}, i18n.t('no_file_selected'))
            return {'CANCELLED'}

        try:
            image = bpy.data.images.load(filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load image: {e}")
            return {'CANCELLED'}

        objs = context.selected_objects or ([context.active_object] if context.active_object else [])
        if not objs:
            self.report({'ERROR'}, i18n.t('select_mesh_for_skin'))
            return {'CANCELLED'}

        # store preview name on scene for UI
        try:
            context.scene.rbx_skin_last_image = image.name
            try:
                image.preview_ensure()
            except Exception:
                pass
        except Exception:
            pass

        for obj in objs:
            if not obj or obj.type != 'MESH':
                continue
            if not obj.data.materials:
                mat = bpy.data.materials.new(name=f"{obj.name}_SkinMat")
                obj.data.materials.append(mat)

            mat = obj.active_material or obj.data.materials[0]
            if mat is None:
                mat = bpy.data.materials.new(name=f"{obj.name}_SkinMat")
                obj.data.materials.append(mat)

            mat.use_nodes = True
            node_tree = getattr(mat, 'node_tree', None)
            if node_tree is None:
                mat.use_nodes = True
                node_tree = mat.node_tree

            nodes = node_tree.nodes
            links = node_tree.links

            bsdf = None
            for n in nodes:
                if getattr(n, 'type', None) == 'BSDF_PRINCIPLED':
                    bsdf = n
                    break
            if bsdf is None:
                bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                bsdf.location = (0, 0)
                out_node = None
                for n in nodes:
                    if getattr(n, 'type', None) == 'OUTPUT_MATERIAL':
                        out_node = n
                        break
                if out_node is None:
                    out_node = nodes.new(type='ShaderNodeOutputMaterial')
                    out_node.location = (300, 0)
                try:
                    links.new(bsdf.outputs.get('BSDF') or bsdf.outputs[0], out_node.inputs.get('Surface') or out_node.inputs[0])
                except Exception:
                    pass

            # create image node
            img_node = nodes.new(type='ShaderNodeTexImage')
            img_node.image = image
            img_node.location = (-600, 0)

            # Mapping / UV controls from Scene
            scene = context.scene
            uv_scale = getattr(scene, 'rbx_skin_uv_scale', (1.0, 1.0))
            uv_offset = getattr(scene, 'rbx_skin_uv_offset', (0.0, 0.0))
            use_mapping = getattr(scene, 'rbx_skin_use_mapping', False)

            # detect active UV map name for this object
            uv_map_name = None
            try:
                if obj.data.uv_layers:
                    uv_map = obj.data.uv_layers.active
                    if uv_map:
                        uv_map_name = uv_map.name
            except Exception:
                uv_map_name = None

            # create mapping chain if requested or scale/offset differs
            try:
                if use_mapping or uv_scale != (1.0, 1.0) or uv_offset != (0.0, 0.0) or uv_map_name:
                    uvmap_node = nodes.new(type='ShaderNodeUVMap')
                    if uv_map_name:
                        try:
                            uvmap_node.uv_map = uv_map_name
                        except Exception:
                            pass
                    mapping_node = nodes.new(type='ShaderNodeMapping')
                    try:
                        mapping_node.inputs.get('Scale').default_value = (uv_scale[0], uv_scale[1], 1.0)
                        mapping_node.inputs.get('Location').default_value = (uv_offset[0], uv_offset[1], 0.0)
                    except Exception:
                        pass
                    try:
                        links.new(uvmap_node.outputs.get('UV') or uvmap_node.outputs[0], mapping_node.inputs.get('Vector') or mapping_node.inputs[0])
                        links.new(mapping_node.outputs.get('Vector') or mapping_node.outputs[0], img_node.inputs.get('Vector') or img_node.inputs[1])
                    except Exception:
                        pass

            except Exception:
                pass

            try:
                base_color = bsdf.inputs.get('Base Color') or bsdf.inputs[0]
                links.new(img_node.outputs.get('Color') or img_node.outputs[0], base_color)
            except Exception:
                pass

        self.report({'INFO'}, i18n.t('skin_applied'))
        return {'FINISHED'}


class RBX_OT_separate_parts(bpy.types.Operator):
    """Separate selected mesh(es) into parts (loose parts or by material)"""
    bl_idname = 'object.rbx_separate_parts'
    bl_label = i18n.t('separate_mesh_parts')
    method: bpy.props.EnumProperty(
        items=(('LOOSE', 'Loose Parts', ''), ('MATERIAL', 'By Material', '')),
        default='LOOSE'
    )

    def execute(self, context):
        objs = context.selected_objects
        if not objs:
            self.report({'ERROR'}, i18n.t('no_mesh_selected'))
            return {'CANCELLED'}

        for obj in list(objs):
            if obj.type != 'MESH':
                continue
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.separate(type=self.method)
            except Exception as e:
                self.report({'ERROR'}, f"Separate failed: {e}")
            bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, i18n.t('separate_done'))
        return {'FINISHED'}

class TOOLBOX_MENU(bpy.types.Panel):
    bl_label = addon_label
    bl_idname = 'RBX_PT_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'RBX Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        # Always-visible update check button (quick access)
        row = layout.row(align=True)
        row.operator('wm.check_update', text=i18n.t('check_for_updates'), icon='FILE_REFRESH')
        if glob_vars.lts_ver is not None:
            # Determine installed version from on-disk __init__.py if possible
            def parse_ver(s):
                try:
                    import re
                    nums = re.findall(r"\\d+", str(s))
                    return tuple(int(x) for x in nums)
                except Exception:
                    return tuple()

            installed_ver = None
            try:
                init_path = os.path.join(addon_path, '__init__.py')
                if os.path.exists(init_path):
                    with open(init_path, 'r', encoding='utf-8') as fh:
                        txt = fh.read()
                    import re
                    m = re.search(r'"version"\s*:\s*\(([^\)]*)\)', txt)
                    if m:
                        nums = [int(x.strip()) for x in m.group(1).split(',') if x.strip().isdigit()]
                        installed_ver = tuple(nums)
            except Exception:
                installed_ver = None

            # Fallback to imported addon_version if disk read failed
            if not installed_ver:
                try:
                    installed_ver = parse_ver(addon_version)
                except Exception:
                    installed_ver = tuple()

            latest_ver = parse_ver(glob_vars.lts_ver)
            update_needed = False
            if latest_ver and installed_ver:
                try:
                    update_needed = latest_ver > installed_ver
                except Exception:
                    # Fallback: perform numeric normalization before comparing
                    import re
                    def _ver_tuple(s):
                        nums = re.findall(r"\d+", str(s))
                        return tuple(int(x) for x in nums) if nums else tuple()
                    update_needed = _ver_tuple(glob_vars.lts_ver) > _ver_tuple(addon_version)
            else:
                import re
                def _ver_tuple(s):
                    nums = re.findall(r"\d+", str(s))
                    return tuple(int(x) for x in nums) if nums else tuple()
                update_needed = _ver_tuple(glob_vars.lts_ver) > _ver_tuple(addon_version)

            if update_needed:
                box = layout.box()
                box.label(text=f"{i18n.t('update_available')} {glob_vars.lts_ver}")
                box.operator('object.url_handler', text=f"{i18n.t('release_notes')} {glob_vars.lts_ver}", icon='DOCUMENTS').rbx_link = 'update'
                if update.operator_state == 'IDLE' and (not glob_vars.need_restart_blender):
                    box.operator('wm.check_update', text=i18n.t('check_for_updates'), icon='FILE_REFRESH')
                    box.operator('wm.install_update', text=i18n.t('install_update'), icon='IMPORT')
                    'elif update.operator_state == "DOWNLOADING":\n                    box.label(text=f"Downloading... {update.download_progress:.2f}%")'
                elif update.operator_state == 'DOWNLOADING':
                    box.prop(update.current_operator, 'progress', text=i18n.t('downloading'), slider=True)
                elif update.operator_state == 'INSTALLING':
                    box.label(text=i18n.t('installing'))
                elif update.operator_state == 'FINISHED':
                    box = layout.box()
                    box.alert = True
                    box.operator('wm.install_update', text=i18n.t('restart_blender'))
                elif update.operator_state == 'ERROR':
                    box = layout.box()
                    box.alert = True
                    box.label(text=i18n.t('error_updateerror_message', update=update), icon='ERROR')
                if glob_vars.need_restart_blender:
                    box.row().label(text=i18n.t('logging_out_complete'), icon='CHECKMARK')
                    box.alert = True
                    box.operator('wm.install_update', text=i18n.t('restart_blender')).restart_only = True
        row = layout.row()
        row.label(text=i18n.t('roblox_authorization'), icon='USER')
        box = layout.box()
        rbx = context.window_manager.rbx
        rbx_installed_dependencies = False
        from oauth.lib import install_dependencies
        if not rbx.is_finished_installing_dependencies:
            box.row().label(text=i18n.t('this_plugin_requires_installation_of'), icon='INFO')
            box.row().label(text=i18n.t('dependencies_the_first_time_it_is_run'))
            box.row().operator(install_dependencies.RBX_OT_install_dependencies.bl_idname, text=i18n.t('installing') if rbx.is_installing_dependencies else i18n.t('install_dependencies'))
        else:
            rbx_installed_dependencies = True
        if rbx.needs_restart:
            box.row().label(text=i18n.t('installation_complete'), icon='CHECKMARK')
            box.alert = True
            box.operator('wm.install_update', text=i18n.t('restart_blender')).restart_only = True
        if rbx_installed_dependencies == True and (not rbx.needs_restart):
            if not rbx.has_called_load_creator:
                from oauth.lib import creator_details
                creator_details.load_creator_details(context.window_manager, context.preferences)
            if not rbx.is_logged_in:
                from oauth.lib import oauth2_login_operators
                button_text_login = 'Logging in...' if rbx.is_processing_login_or_logout else i18n.t('log_in')
                box.row().operator(oauth2_login_operators.RBX_OT_oauth2_login.bl_idname, text=button_text_login)
                if bpy.ops.rbx.oauth2_cancel_login.poll():
                    box.row().operator(oauth2_login_operators.RBX_OT_oauth2_cancel_login.bl_idname)
            else:
                try:
                    from oauth.lib import user_thumbnail
                    _uid = glob_vars.get_login_info().get('user_id')
                    if _uid:
                        user_thumbnail.schedule_fetch(_uid)
                    _icon_id = user_thumbnail.get_icon_id()
                    if _icon_id:
                        box.template_icon(_icon_id, scale=3.0)
                except Exception:
                    pass
                top_row_creator = box.row(align=True)
                try:
                    from oauth.lib.oauth2_client import RbxOAuth2Client
                    oauth2_client = RbxOAuth2Client(rbx)
                    top_row_creator.label(text=i18n.t('hello_rbxname', rbx=rbx))
                except Exception as exception:
                    self.report({'ERROR'}, f'Failed to display user name: {str(exception)}\n{traceback.format_exc()}')
                    top_row_creator.label(text=i18n.t('hello_user_error'), icon='ERROR')
                from oauth.lib import oauth2_login_operators
                button_text_logout = 'Working...' if rbx.is_processing_login_or_logout else i18n.t('log_out')
                top_row_creator.operator(oauth2_login_operators.RBX_OT_oauth2_logout.bl_idname, text=button_text_logout)
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_readme else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_readme', icon=icon, icon_only=True)
        row.label(text=i18n.t('readme'), icon='ASSET_MANAGER')
        if context.scene.subpanel_readme:
            box = layout.box()
            box.operator('object.url_handler', text=i18n.t('read_instructions_credits'), icon='ARMATURE_DATA').rbx_link = 'Credits and Instructions'
            box.operator('object.url_handler', text=i18n.t('read_version_log'), icon='CON_ARMATURE').rbx_link = 'Version_log'
            box = layout.box()
            box.label(text=i18n.t('r15_rigs_are_taken_from_here'))
            box.operator('object.url_handler', text=i18n.t('roblox_github'), icon='URL').rbx_link = 'rbx github'
            box.label(text=i18n.t('r6_rig_taken_from_here'))
            box.operator('object.url_handler', text=i18n.t('nuke_youtube'), icon='URL').rbx_link = 'rbx nuke'
            box.label(text=i18n.t('you_can_see_here_how_to_link'))
            box.label(text=i18n.t('texture_to_r6_rig'))
            '\n            if rbx_assets_set != 1:\n                box.label(text = "To unlock additional features")\n                box.label(text = "Specify folder with UGC")\n                box.label(text = "blend file \'Bounds.blend\'")\n            row = layout.row()\n            box.prop(addon_assets, rbx_folder)\n            if rbx_assets_set == 1:\n                box.label(text = "\'Bounds.blend\' linked to addon")\n            if rbx_assets_set == 2:\n                box.label(text = "\'Bounds.blend\' not found")\n            '
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_hdri else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_hdri', icon=icon, icon_only=True)
        row.label(text=i18n.t('hdri_templates'), icon='WORLD')
        if context.scene.subpanel_hdri:
            box = layout.box()
            box.label(text=i18n.t('blender_builtin_hdris'), icon='NODE_MATERIAL')
            box.prop(rbx_prefs, 'rbx_hdri_enum')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.rbx_button_hdrifull', text=i18n.t('set_as_hdri')).rbx_hdri = 'hdri'
            try:
                wrld = bpy.context.scene.world.name
            except:
                pass
            else:
                box.label(text=i18n.t('current_world_controls'))
                wrld_0 = bpy.data.worlds[wrld].node_tree.nodes['Background'].inputs['Strength']
                wrld_1 = None
                if wrld == 'HDRI':
                    wrld_1 = bpy.data.worlds[wrld].node_tree.nodes['Mapping'].inputs['Rotation']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('brightness'))
                split.prop(wrld_0, 'default_value', text='')
                if wrld == 'HDRI':
                    split = box.split(factor=0.5)
                    col = split.column(align=True)
                    col.label(text=i18n.t('rotationn'))
                    split.prop(wrld_1, 'default_value', text='')
            box = layout.box()
            box.label(text=i18n.t('simple_skybox'), icon='WORLD_DATA')
            box.prop(rbx_prefs, 'rbx_sky_enum')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.rbx_button_hdrifull', text=i18n.t('set_sky')).rbx_hdri = 'sky'
            try:
                sky = bpy.data.objects['Sky Sphere']
            except:
                pass
            else:
                box.label(text=i18n.t('skybox_controls'))
                sky_0 = bpy.data.objects['Sky Sphere'].active_material.node_tree.nodes['Mapping'].inputs['Location']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('rotation'))
                split.prop(sky_0, 'default_value', text='')
            box.label(text=i18n.t('you_may_setup_your_own'))
            box.label(text=' Skybox in Shading tab')
            box = layout.box()
            box.operator('object.button_cmr', text=i18n.t('add_animated_staging'), icon='IMPORT').cmr = 'staging'
            try:
                bpy.data.objects['Staging Camera']
            except:
                pass
            else:
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('camera'))
                split.operator('object.button_cmr', text=i18n.t('set_active')).cmr = 'staging-active'
            try:
                bkdrp = bpy.data.objects['Floor Plane']
            except:
                pass
            else:
                bkdrp_0 = bpy.data.objects['Floor Plane'].active_material.node_tree.nodes['Principled BSDF'].inputs['Base Color']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('backdrop'))
                split.prop(bkdrp_0, 'default_value', text='')
            box = layout.box()
            box.operator('object.button_cmr', text=i18n.t('add_avatar_editor_room'), icon='IMPORT').cmr = 'edtr_append'
            try:
                bpy.data.objects['Avatar Editor Camera']
            except:
                pass
            else:
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('camera'))
                split.operator('object.button_cmr', text=i18n.t('set_active')).cmr = 'edtr-active'
            box = layout.box()
            box.operator('object.button_cmr', text=i18n.t('add_roblox_baseplate'), icon='IMPORT').cmr = 'bsplt_append'
        if rbx.is_logged_in:
            row = layout.row()
            icon = 'DOWNARROW_HLT' if context.scene.subpanel_imp_beta else 'RIGHTARROW'
            row.prop(context.scene, 'subpanel_imp_beta', icon=icon, icon_only=True)
            row.label(text=i18n.t('import_beta'), icon='IMPORT')
            if context.scene.subpanel_imp_beta:
                addon_prefs = context.preferences.addons['test321'].preferences
                if not addon_prefs.accepted_terms_of_use:
                    box = layout.box()
                    box.label(text=i18n.t('please_accept_the_terms_of_use'), icon='INFO')
                    box.label(text=i18n.t('before_using_import_beta'))
                    box.operator('object.rbx_terms_of_use', text=i18n.t('terms_of_use'), icon='BOOKMARKS').action = 'SHOW'
                else:
                    box = layout.box()
                    box.label(text='Avatar import', icon='COMMUNITY')
                    row = box.row()
                    row.prop(rbx_prefs, 'rbx_username_entered', text='Username/ID')
                    box.prop(rbx_prefs, 'rbx_avatar_rig_type', text='Rig')
                    row = box.row(align=True)
                    row.operator('object.rbx_import_avatar', text='Import my avatar', icon='IMPORT').source = 'SELF'
                    row.operator('object.rbx_import_avatar', text='Import by username/ID', icon='IMPORT').source = 'USER_INPUT'
                    box.separator()
                    box = layout.box()
                    row_title = box.row()
                    row_title.label(text=i18n.t('enter_id_or_url'))
                    row_title.operator('object.rbx_import_discovery_info_popup', text='', icon='INFO')
                    row = box.row()
                    row.enabled = not rbx_prefs.rbx_import_beta_active
                    row.prop(rbx_prefs, 'rbx_item_field_entry', text='')
                    row = box.row()
                    row.enabled = not rbx_prefs.rbx_import_beta_active
                    row.operator('object.rbx_import_discovery', text=i18n.t('asset_discovery'))
                    box_reset = box.box()
                    if rbx_prefs.rbx_import_beta_active:
                        box_reset.alert = True
                    box_reset.operator('object.rbx_import_reset', text=i18n.t('reset'))
                    if glob_vars.rbx_imp_error:
                        for (idx, error_line) in enumerate(glob_vars.rbx_imp_error.split('\n')):
                            if idx == 0:
                                box_reset.label(text=error_line, icon='ERROR')
                            else:
                                box_reset.label(text=error_line)
                    if hasattr(glob_vars, 'discovered_items_data') and glob_vars.discovered_items_data:
                        has_items = any(glob_vars.discovered_items_data.values())
                        if has_items:
                            box = layout.box()
                            box.label(text=i18n.t('discovered_items'), icon='PREFERENCES')
                            box.prop(rbx_prefs, 'rbx_import_filter', text='Filter')
                            if glob_vars.rbx_asset_name:
                                box.label(text=i18n.t('name_glob_varsrbx_asset_name', glob_vars=glob_vars))
                            if glob_vars.rbx_asset_type:
                                box.label(text=i18n.t('type_glob_varsrbx_asset_type', glob_vars=glob_vars))
                            if glob_vars.rbx_asset_creator:
                                box.label(text=i18n.t('creator_glob_varsrbx_asset_creator', glob_vars=glob_vars))
                            try:
                                if glob_vars.rbx_asset_name_clean:
                                    rbx_asset_img_prev = bpy.data.images.get(glob_vars.rbx_asset_name_clean + '.png')
                                    if rbx_asset_img_prev:
                                        rbx_asset_img_prev.preview_ensure()
                                        box.template_icon(rbx_asset_img_prev.preview.icon_id, scale=10.0)
                            except:
                                pass
                            from test321.func_import_v2 import rbx_import_discovery as discovery_config

                            filter_text = (rbx_prefs.rbx_import_filter or '').strip().lower()
                            if filter_text:
                                matches_box = box.box()
                                matches_box.label(text='Matches', icon='VIEWZOOM')
                                match_lines = 0
                                for (cat_name, items) in glob_vars.discovered_items_data.items():
                                    for item in items:
                                        name = str(item.get('name', ''))
                                        if filter_text in name.lower():
                                            matches_box.label(text=f"{cat_name}: {name}")
                                            match_lines += 1
                                            if match_lines >= 15:
                                                break
                                    if match_lines >= 15:
                                        break
                                if match_lines == 0:
                                    matches_box.label(text='No matches', icon='INFO')

                            def draw_discovery_category(layout, category_name, icon, enum_prop, download_operator_text):
                                box = layout.box()
                                row_header = box.row()
                                row_header.alert = True
                                row_header.label(text=category_name, icon=icon)
                                if category_name != 'Classics':
                                    row_header.operator('object.rbx_import_discovery_options', text='', icon='PREFERENCES').category = category_name
                                box.separator()
                                box.prop(rbx_prefs, enum_prop, text='')
                                if category_name == 'Dynamic Head' and getattr(glob_vars, 'rbx_default_head_used', False):
                                    col_info = box.column(align=True)
                                    col_info.label(text=i18n.t('dynamic_head_not_found_in_bundle'), icon='INFO')
                                    col_info.label(text=i18n.t('default_is_used'))
                                box.separator()
                                box.separator()
                                box.operator('object.rbx_import_discovery_download', text=download_operator_text).category = category_name
                                if category_name not in ('Armature', 'Models'):
                                    box.operator('object.rbx_import_discovery_open_folder', text=i18n.t('open_folder')).category = category_name
                                elif getattr(glob_vars, 'rbx_armature_warning_active', False):
                                    col_info = box.column(align=True)
                                    col_info.label(text=i18n.t('armatures_for_older_meshes'), icon='ERROR')
                                    col_info.label(text=i18n.t('below_v400_are_not_supported'))
                            categories_to_draw = []
                            def _has_filter_match(cat):
                                if not filter_text:
                                    return True
                                items = glob_vars.discovered_items_data.get(cat, [])
                                return any(filter_text in str(i.get('name', '')).lower() for i in items)
                            if glob_vars.discovered_items_data.get('Body Parts'):
                                if _has_filter_match('Body Parts'):
                                    categories_to_draw.append(('Body Parts', 'OUTLINER_OB_ARMATURE', 'rbx_enum_body_parts', 'Download Body Parts'))
                            if glob_vars.discovered_items_data.get('Accessory'):
                                if _has_filter_match('Accessory'):
                                    categories_to_draw.append(('Accessory', 'MOD_CLOTH', 'rbx_enum_accessory', 'Download Accessories'))
                            if glob_vars.discovered_items_data.get('Dynamic Head'):
                                if _has_filter_match('Dynamic Head'):
                                    categories_to_draw.append(('Dynamic Head', 'MONKEY', 'rbx_enum_dynamic_head', 'Download Dynamic Head'))
                            if glob_vars.discovered_items_data.get('Layered Cloth'):
                                if _has_filter_match('Layered Cloth'):
                                    categories_to_draw.append(('Layered Cloth', 'MOD_CLOTH', 'rbx_enum_layered_cloth', 'Download Layered Cloth'))
                            if glob_vars.discovered_items_data.get('Face Parts'):
                                if _has_filter_match('Face Parts'):
                                    categories_to_draw.append(('Face Parts', 'FACESEL', 'rbx_enum_face_parts', 'Download Face Parts'))
                            if glob_vars.discovered_items_data.get('Classics'):
                                if _has_filter_match('Classics'):
                                    categories_to_draw.append(('Classics', 'MOD_CLOTH', 'rbx_enum_classics', 'Download Classics'))
                            if glob_vars.discovered_items_data.get('Gear'):
                                if _has_filter_match('Gear'):
                                    categories_to_draw.append(('Gear', 'MODIFIER', 'rbx_enum_gear', 'Download Gear'))
                            armature_relevant_cats = ['Body Parts', 'Dynamic Head', 'Layered Cloth', 'Face Parts']
                            if any((glob_vars.discovered_items_data.get(cat) for cat in armature_relevant_cats)):
                                if _has_filter_match('Body Parts') or _has_filter_match('Dynamic Head') or _has_filter_match('Layered Cloth') or _has_filter_match('Face Parts'):
                                    categories_to_draw.append(('Armature', 'OUTLINER_OB_ARMATURE', 'rbx_arma_enum', 'Download Armature'))
                            if glob_vars.discovered_items_data.get('Models'):
                                if _has_filter_match('Models'):
                                    categories_to_draw.append(('Models', 'MESH_CUBE', 'rbx_enum_models', 'Download Model'))
                            if glob_vars.discovered_items_data.get('Places'):
                                if _has_filter_match('Places'):
                                    categories_to_draw.append(('Places', 'WORLD', 'rbx_enum_places', 'Download Place'))
                            for (cat_name, icon, enum, dl_text) in categories_to_draw:
                                draw_discovery_category(layout, cat_name, icon, enum, dl_text)
                            if glob_vars.discovered_items_data.get('Animations'):
                                box = layout.box()
                                row_header = box.row()
                                row_header.alert = True
                                row_header.label(text=i18n.t('animations'), icon='ACTION')
                                box.separator()
                                box.label(text=i18n.t('target_armature'))
                                box.prop(rbx_prefs, 'rbx_anim_armature_target', text='')
                                box.separator()
                                box.prop(rbx_prefs, 'rbx_enum_animations', text='')
                                box.operator('object.rbx_import_discovery_download', text=i18n.t('check_alt_animations')).category = 'Animations'
                                anim_subs = getattr(glob_vars, 'rbx_anim_sub_items', [])
                                if anim_subs:
                                    box.separator()
                                    box.label(text=i18n.t('found_lenanim_subs_animations'))
                                    for (idx, sub) in enumerate(anim_subs):
                                        box.operator('object.rbx_import_discovery_download', text=sub.get('name', f'Animation {idx}'), icon='PLAY').category = f'Animations_Apply_{idx}'
                            if len(categories_to_draw) > 1:
                                box_dl_all = layout.box()
                                box_dl_all.label(text=i18n.t('process_all'), icon='IMPORT')
                                box_dl_all.label(text=i18n.t('select_checkboxes_in_above_menus'))
                                box_dl_all.operator('object.rbx_import_discovery_download', text=i18n.t('download_everything')).category = 'ALL_CATEGORIES'
                    box_tmp = layout.box()
                    box_tmp.operator('object.rbx_open_tmp_folder', text=i18n.t('open_junk_tmp_folder'), icon='FILE_FOLDER')
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_bounds else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_bounds', icon=icon, icon_only=True)
        row.label(text=i18n.t('accessory_bounds'), icon='CUBE')
        if context.scene.subpanel_bounds:
            box = layout.box()
            box.prop(rbx_prefs, 'rbx_bnds_enum', text=i18n.t('ugc'))
            box.prop(rbx_prefs, 'rbx_bnds_hide')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.button_bnds', text=i18n.t('spawn')).bnds = 'UGC'
            box = layout.box()
            box.prop(rbx_prefs, 'rbx_bnds_avatar_enum', text=i18n.t('avatars'))
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.button_bnds', text=i18n.t('spawn')).bnds = 'AVA'
            box = layout.box()
            box.prop(rbx_prefs, 'rbx_bnds_lc_enum', text=i18n.t('lc_6907b869'))
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.button_bnds', text=i18n.t('spawn')).bnds = 'LC'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_dummy else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_dummy', icon=icon, icon_only=True)
        row.label(text=i18n.t('dummy'), icon='OUTLINER_OB_ARMATURE')
        if context.scene.subpanel_dummy:
            box = layout.box()
            box.label(text=i18n.t('dummies'))
            box.prop(rbx_prefs, 'rbx_dum_enum', text='')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.button_dmmy', text=i18n.t('spawn')).dmy = 'Dummy'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_rigs else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_rigs', icon=icon, icon_only=True)
        row.label(text=i18n.t('rigs'), icon='OUTLINER_DATA_ARMATURE')
        if context.scene.subpanel_rigs:
            box = layout.box()
            box.label(text=i18n.t('roblox_rigged_models'))
            box.operator('object.button_dmmy', text=i18n.t('r15_blocky_rig')).dmy = 'R15 Blocky Rig'
            box.operator('object.button_dmmy', text=i18n.t('r15_woman_rig')).dmy = 'R15 Woman Rig'
            box.operator('object.button_dmmy', text=i18n.t('plushie_template')).dmy = 'Plushie Template'
            box = layout.box()
            box.label(text=i18n.t('iixenix_rigs'))
            box.operator('object.button_dmmy', text=i18n.t('multirig')).dmy = 'Multirig'
            box.operator('object.button_dmmy', text=i18n.t('multirig_faceless')).dmy = 'Multirig_faceless'
            box = layout.box()
            box.label(text=i18n.t('paribes_rig'))
            aepbr_path = os.path.join(addon_path, glob_vars.rbx_aepbr_fldr)
            folder_exists = os.path.exists(aepbr_path)
            blend_files = glob.glob(os.path.join(aepbr_path, '*.blend'))
            if folder_exists and blend_files:
                box.operator('object.button_dmmy', text=i18n.t('aepbr')).dmy = 'aepbr'
                if glob_vars.aepbr_lts_ver is not None:
                    aepbr_cur_ver = get_aepbr_cur_ver()
                    if glob_vars.aepbr_lts_ver > aepbr_cur_ver:
                        box.label(text='')
                        box.label(text='- - - - - - - ')
                        box.label(text=i18n.t('update_available_aepbr_cur_ver_glob_vars', aepbr_cur_ver=aepbr_cur_ver, glob_vars=glob_vars))
                        box.label(text=glob_vars.aepbr_lts_title)
                        if update_aepbr.aepbr_operator_state == 'IDLE':
                            box.operator('wm.update_aepbr', text=i18n.t('install_update'), icon='IMPORT')
                            box.operator('object.url_handler', text=i18n.t('release_notes_vglob_varsaepbr_lts_ver', glob_vars=glob_vars), icon='DOCUMENTS').rbx_link = 'aepbr notes'
                        elif update_aepbr.aepbr_operator_state == 'DOWNLOADING':
                            box.prop(update_aepbr.aepbr_current_operator, 'progress', text=i18n.t('downloading'), slider=True)
                        elif update_aepbr.aepbr_operator_state == 'INSTALLING':
                            box.label(text=i18n.t('installing'))
                        elif update_aepbr.aepbr_operator_state == 'ERROR':
                            box = layout.box()
                            box.alert = True
                            box.label(text=i18n.t('error_update_aepbraepbr_error_message', update_aepbr=update_aepbr), icon='ERROR')
            elif update_aepbr.aepbr_operator_state == 'IDLE':
                if glob_vars.aepbr_lts_ver is None:
                    box.enabled = False
                    box.operator('wm.update_aepbr', text=i18n.t('dowload_rig_vglob_varsaepbr_lts_ver', glob_vars=glob_vars), icon='IMPORT')
                    box.label(text=i18n.t('no_inernet_connection'), icon='ERROR')
                else:
                    box.operator('wm.update_aepbr', text=i18n.t('dowload_rig_vglob_varsaepbr_lts_ver', glob_vars=glob_vars), icon='IMPORT')
            elif update_aepbr.aepbr_operator_state == 'DOWNLOADING':
                box.prop(update_aepbr.aepbr_current_operator, 'progress', text=i18n.t('downloading'), slider=True)
            elif update_aepbr.aepbr_operator_state == 'INSTALLING':
                box.label(text=i18n.t('installing'))
            elif update_aepbr.aepbr_operator_state == 'ERROR':
                box = layout.box()
                box.alert = True
                box.label(text=i18n.t('error_update_aepbraepbr_error_message', update_aepbr=update_aepbr), icon='ERROR')
            box = layout.box()
            box.operator('object.url_handler', text=i18n.t('aepbr_discord'), icon='URL').rbx_link = 'aepbr discord'
            box = layout.box()
            box.label(text=i18n.t('r6_from_nuke_yt'))
            box.operator('object.button_dmmy', text=i18n.t('rigged_r6')).dmy = 'Rigged R6'
            box.label(text='')
            box.label(text=i18n.t('wear_character_select_armature'))
            box.label(text=i18n.t('currently_only_r6_rig_is_supported'))
            box.operator('object.button_wear', text=i18n.t('modify_character')).rbx_cloth = 'mod'
            cloth_panel = False
            try:
                rbx_object = bpy.context.selected_objects
                if len(rbx_object) == 1:
                    rbx_object = bpy.context.selected_objects[0]
                    if rbx_object.type == 'ARMATURE':
                        if 'cloth_mod' in rbx_object.name:
                            cloth_panel = True
                        else:
                            cloth_panel = False
                    else:
                        cloth_panel = False
                else:
                    cloth_panel = False
            except:
                pass
            if cloth_panel == True:
                box = layout.box()
                box.label(text=i18n.t('head'))
                rbx_cloth_head = bpy.data.materials[f'R6 Head_{rbx_object.name}'].node_tree.nodes['R6 Cloth']
                cloth_head = rbx_cloth_head.inputs['Skin Tone']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('skin_tone'))
                split.prop(cloth_head, 'default_value', text='')
                if glob_vars.rbx_face_filename == None:
                    box.label(text=i18n.t('loaded_face_none'))
                else:
                    box.label(text=i18n.t('loaded_face_glob_varsrbx_face_name', glob_vars=glob_vars))
                box.label(text=i18n.t('enter_face_id_or_url'))
                box.prop(rbx_prefs, 'rbx_face', text='')
                box.operator('object.button_wear', text=i18n.t('import')).rbx_cloth = 'face'
                if glob_vars.rbx_face_netw_error != None:
                    box.label(text=glob_vars.rbx_face_netw_error, icon='ERROR')
                box = layout.box()
                box.label(text=i18n.t('shirt'))
                rbx_cloth_shirt = bpy.data.materials[f'R6 Shirt_{rbx_object.name}'].node_tree.nodes['R6 Cloth']
                cloth_shirt = rbx_cloth_shirt.inputs['Skin Tone']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('skin_tone'))
                split.prop(cloth_shirt, 'default_value', text='')
                if glob_vars.rbx_shirt_filename == None:
                    box.label(text=i18n.t('loaded_shirt_none'))
                else:
                    box.label(text=i18n.t('loaded_shirt_glob_varsrbx_shirt_name', glob_vars=glob_vars))
                box.label(text=i18n.t('enter_shirt_id_or_url'))
                box.prop(rbx_prefs, 'rbx_shirt', text='')
                box.operator('object.button_wear', text=i18n.t('import')).rbx_cloth = 'shirt'
                if glob_vars.rbx_shirt_netw_error != None:
                    box.label(text=glob_vars.rbx_shirt_netw_error, icon='ERROR')
                box = layout.box()
                box.label(text=i18n.t('torso'))
                rbx_cloth_torso = bpy.data.materials[f'R6 Torso_{rbx_object.name}'].node_tree.nodes['R6 Cloth']
                cloth_torso = rbx_cloth_torso.inputs['Skin Tone']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('skin_tone'))
                split.prop(cloth_torso, 'default_value', text='')
                if glob_vars.rbx_shirt_filename == None:
                    box.label(text=i18n.t('loaded_shirt_none'))
                else:
                    box.label(text=i18n.t('loaded_shirt_glob_varsrbx_shirt_name', glob_vars=glob_vars))
                if glob_vars.rbx_pants_filename == None:
                    box.label(text=i18n.t('loaded_pants_none'))
                else:
                    box.label(text=i18n.t('loaded_pants_glob_varsrbx_pants_name', glob_vars=glob_vars))
                box = layout.box()
                box.label(text=i18n.t('pants'))
                rbx_cloth_pants = bpy.data.materials[f'R6 Pants_{rbx_object.name}'].node_tree.nodes['R6 Cloth']
                cloth_pants = rbx_cloth_pants.inputs['Skin Tone']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('skin_tone'))
                split.prop(cloth_pants, 'default_value', text='')
                if glob_vars.rbx_pants_filename == None:
                    box.label(text=i18n.t('loaded_pants_none'))
                else:
                    box.label(text=i18n.t('loaded_pants_glob_varsrbx_pants_name', glob_vars=glob_vars))
                box.label(text=i18n.t('enter_pants_id_or_url'))
                box.prop(rbx_prefs, 'rbx_pants', text='')
                box.operator('object.button_wear', text=i18n.t('import')).rbx_cloth = 'pants'
                if glob_vars.rbx_pants_netw_error != None:
                    box.label(text=glob_vars.rbx_pants_netw_error, icon='ERROR')
                box.label(text='')
                box.operator('object.button_wear', text=i18n.t('textures_folder')).rbx_cloth = 'folder'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_hair else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_hair', icon=icon, icon_only=True)
        row.label(text=i18n.t('hairs'), icon='OUTLINER_OB_FORCE_FIELD')
        if context.scene.subpanel_hair:
            box = layout.box()
            box.label(text=i18n.t('dummie_heads_only'))
            box.prop(rbx_prefs, 'rbx_dum_hd_enum', text='')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.button_hair', text=i18n.t('spawn')).rbx_hair = 'Dummy_head'
            box.separator()
            split = box.split(factor=0.7)
            col = split.column(align=True)
            col.label(text=i18n.t('starter_hair_template'))
            split.operator('object.button_hair', text=i18n.t('add')).rbx_hair = 'hair_template'
            box = layout.box()
            box.label(text=i18n.t('bake_hair_texture'))
            box.operator('object.button_hair', text=i18n.t('add_hair_shader')).rbx_hair = 'hair_shader'
            try:
                rbx_hair_color = bpy.data.objects['Hair Color']
            except:
                pass
            else:
                rbx_hair_cntrl = rbx_hair_color.active_material.node_tree.nodes['Hair shader v.2.0']
                box.label(text=i18n.t('hair_color_controls'))
                hrs_0 = rbx_hair_cntrl.inputs['Hair Color']
                hrs_1 = rbx_hair_cntrl.inputs['Hair Strands']
                hrs_2 = rbx_hair_cntrl.inputs['Strands Color']
                hrs_3 = rbx_hair_cntrl.inputs['Highlight Color']
                hrs_4 = rbx_hair_cntrl.inputs['Highlight Scale']
                hrs_5 = rbx_hair_cntrl.inputs['Top Position']
                hrs_6 = rbx_hair_cntrl.inputs['Bottom Position']
                hrs_7 = rbx_hair_cntrl.inputs['Bumps']
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('hair_color'))
                split.prop(hrs_0, 'default_value', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('hair_strands'))
                split.prop(hrs_1, 'default_value', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('strands_color'))
                split.prop(hrs_2, 'default_value', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('highlight_color'))
                split.prop(hrs_3, 'default_value', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('highlight_scale'))
                split.prop(hrs_4, 'default_value', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('top_position'))
                split.prop(hrs_5, 'default_value', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('bottom_position'))
                split.prop(hrs_6, 'default_value', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('bumps'))
                split.prop(hrs_7, 'default_value', text='')
                box.separator()
                split = box.split(factor=0.3)
                col = split.column(align=True)
                col.label(text='')
                split.operator('object.button_hair', text=i18n.t('bake_texture')).rbx_hair = 'hair_bake'
                box.operator('object.button_hair', text=i18n.t('view_image')).rbx_hair = 'hair_save'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_lc else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_lc', icon=icon, icon_only=True)
        row.label(text=i18n.t('layered_cloth'), icon='MATCLOTH')
        if context.scene.subpanel_lc:
            box = layout.box()
            box.label(text=i18n.t('cages'))
            box.prop(rbx_prefs, 'rbx_lc_dum_enum', text='')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.operator('object.rbx_button_lc', text=i18n.t('cages')).rbx_lc = '_Cage'
            split.operator('object.rbx_button_lc', text=i18n.t('armature')).rbx_lc = '_Arma'
            box = layout.box()
            try:
                if len(bpy.context.selected_objects) == 1:
                    for i in bpy.context.selected_objects:
                        if i.type == 'ARMATURE':
                            box.prop(bpy.context.object, 'show_in_front', text=i18n.t('show_bones_infront'))
                            box.prop(bpy.context.object.data, 'show_names', text=i18n.t('show_bone_names'))
                else:
                    box.enabled = False
                    box.prop(rbx_prefs, 'rbx_bn_disabled', text=i18n.t('show_bones_infront'))
                    box.prop(rbx_prefs, 'rbx_bn_disabled', text=i18n.t('show_bone_names'))
            except:
                box.enabled = False
                box.prop(rbx_prefs, 'rbx_bn_disabled', text=i18n.t('show_bones_infront'))
                box.prop(rbx_prefs, 'rbx_bn_disabled', text=i18n.t('show_bone_names'))
            box = layout.box()
            row_title = box.row()
            row_title.label(text=i18n.t('lc_animation_test'))
            row_title.operator('object.rbx_lc_anim_test_info_popup', text='', icon='INFO')
            box.label(text=i18n.t('1_select_lc_armature'))
            box.prop_search(scene, 'rbx_lc_anim_armature', scene, 'objects')
            box.label(text=i18n.t('2_select_rig_to_spawn'))
            box.prop(rbx_prefs, 'rbx_lc_anim_v2_rig_enum', text='')
            box.separator()
            box.operator('object.rbx_lc_anim_v2', text=i18n.t('spawn_rig'), icon='ARMATURE_DATA')
            from ..func_import_v2.func_lc_animations import _is_rig_spawned
            if _is_rig_spawned():
                box.separator()
                box.label(text=i18n.t('animations_6c85be98'))
                row = box.row(align=True)
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('idle'), icon='ARMATURE_DATA').anim_type = 'IDLE'
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('walk'), icon='ARMATURE_DATA').anim_type = 'WALK'
                row = box.row(align=True)
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('move'), icon='ARMATURE_DATA').anim_type = 'MOVE'
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('run'), icon='ARMATURE_DATA').anim_type = 'RUN'
                row = box.row(align=True)
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('swim'), icon='ARMATURE_DATA').anim_type = 'SWIM'
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('climb'), icon='ARMATURE_DATA').anim_type = 'CLIMB'
                row = box.row(align=True)
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('jump'), icon='ARMATURE_DATA').anim_type = 'JUMP'
                row.operator('object.rbx_lc_anim_v2_add_anim', text=i18n.t('fall'), icon='ARMATURE_DATA').anim_type = 'FALL'
                box.separator()
                row = box.row()
                play_icon = 'PAUSE' if _is_rig_spawned() and __import__('test321.func_import_v2.func_lc_animations', fromlist=['_LC_Anim_V2_Globals'])._LC_Anim_V2_Globals.animationIsPlaying else 'PLAY'
                row.operator('object.rbx_lc_anim_v2_play', text=i18n.t('play_pause'), icon=play_icon)
                row.operator('object.rbx_lc_anim_v2_delete', text=i18n.t('delete_rig'), icon='TRASH')
                box.prop(scene, 'rbx_lc_anim_scrub', text=i18n.t('scrub'), slider=True)
                from ..func_import_v2.func_lc_animations import _LC_Anim_V2_Globals
                cur_speed = round(_LC_Anim_V2_Globals.currentSpeed, 2)
                box.label(text=i18n.t('speed'))
                row = box.row(align=True)
                op = row.operator('object.rbx_lc_anim_v2_speed', text=i18n.t('01x_07c8fdc8'), depress=cur_speed == 0.1)
                op.speed = 0.1
                op = row.operator('object.rbx_lc_anim_v2_speed', text=i18n.t('025x_a505df0a'), depress=cur_speed == 0.25)
                op.speed = 0.25
                op = row.operator('object.rbx_lc_anim_v2_speed', text=i18n.t('05x_60c9b4d8'), depress=cur_speed == 0.5)
                op.speed = 0.5
                op = row.operator('object.rbx_lc_anim_v2_speed', text=i18n.t('1x_38684612'), depress=cur_speed == 1.0)
                op.speed = 1.0
            box = layout.box()
            box.label(text=i18n.t('roblox_samples_from_github'))
            box.prop(rbx_prefs, 'rbx_lc_spl_enum', text='')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.rbx_button_lc', text=i18n.t('spawn')).rbx_lc = 'sample'
            box = layout.box()
            box.operator('object.url_handler', text=i18n.t('roblox_github'), icon='URL').rbx_link = 'rbx github'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_ava else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_ava', icon=icon, icon_only=True)
        row.label(text=i18n.t('avatars'), icon='COMMUNITY')
        if context.scene.subpanel_ava:
            box = layout.box()
            box.label(text=i18n.t('avatar_templates'))
            box.prop(rbx_prefs, 'rbx_ava_enum', text='')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text='')
            split.operator('object.rbx_button_ava', text=i18n.t('spawn')).rbx_ava = 'avatar'
            box = layout.box()
            box.label(text=i18n.t('mesh_custom_properties'))
            box.operator('object.rbx_button_ava', text=i18n.t('clean_up_all')).rbx_ava = 'clear'
            row_facs = box.row()
            row_facs.enabled = len(bpy.context.selected_objects) == 1
            row_facs.operator('object.rbx_button_ava', text=i18n.t('add_facs_properties_head_only')).rbx_ava = 'add_facs'
            row_facs2 = box.row()
            is_arma_selected = len(bpy.context.selected_objects) == 1 and bpy.context.selected_objects[0].type == 'ARMATURE'
            row_facs2.enabled = is_arma_selected
            row_facs2.operator('object.rbx_button_ava', text=i18n.t('add_facs_animation_arma')).rbx_ava = 'add_facs_anim'
            if not is_arma_selected:
                glob_vars.rbx_facs_anim_error = None
            if getattr(glob_vars, 'rbx_facs_anim_error', None):
                import textwrap
                err_text = glob_vars.rbx_facs_anim_error
                wrapped = textwrap.wrap(err_text, width=40)
                for (i, line) in enumerate(wrapped):
                    box.label(text=line, icon='ERROR' if i == 0 else 'NONE')
            box = layout.box()
            box.label(text=i18n.t('select_objects_to_remove_000'))
            box.label(text=i18n.t('ps_not_always_works'))
            box.operator('object.rbx_button_ava', text=i18n.t('rename_all')).rbx_ava = 'rename'
            box = layout.box()
            box.label(text=i18n.t('hide_all_att_in_selected'))
            box.operator('object.rbx_button_ava', text=i18n.t('hide_all')).rbx_ava = 'hide'
            box.operator('object.rbx_button_ava', text=i18n.t('unhide_them')).rbx_ava = 'unhide'
            box.label(text=i18n.t('only_the_ones_you_hide_before'))
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_cams else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_cams', icon=icon, icon_only=True)
        row.label(text=i18n.t('cameras_and_lights'), icon='CAMERA_DATA')
        if context.scene.subpanel_cams:
            box = layout.box()
            box.operator('object.button_cmr', text=i18n.t('add_4_cameras_setup'), icon='IMPORT').cmr = 'append'
            try:
                bpy.data.objects['Camera_F']
            except:
                pass
            else:
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('camera_front'))
                split.operator('object.button_cmr', text=i18n.t('set_active')).cmr = 'Camera_F_active'
            try:
                bpy.data.objects['Camera_B']
            except:
                pass
            else:
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('camera_back'))
                split.operator('object.button_cmr', text=i18n.t('set_active')).cmr = 'Camera_B_active'
            try:
                bpy.data.objects['Camera_L']
            except:
                pass
            else:
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text='  Camera Left:')
                split.operator('object.button_cmr', text=i18n.t('set_active')).cmr = 'Camera_L_active'
            try:
                bpy.data.objects['Camera_R']
            except:
                pass
            else:
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text=i18n.t('camera_right'))
                split.operator('object.button_cmr', text=i18n.t('set_active')).cmr = 'Camera_R_active'
            try:
                bpy.context.active_object.name
            except:
                pass
            else:
                for i in range(len(glob_vars.cams)):
                    if bpy.context.active_object.name == glob_vars.cams[i]:
                        split = box.split(factor=0.4)
                        col = split.column(align=True)
                        col.label(text='')
                        split.operator('object.button_cmr', text=i18n.t('preview'), icon='HIDE_OFF').cmr = 'preview'
            try:
                bpy.context.active_object.name
            except:
                pass
            else:
                for i in range(len(glob_vars.cams)):
                    if bpy.context.active_object.name == glob_vars.cams[i]:
                        box.prop(bpy.context.scene.render, 'film_transparent', text=i18n.t('transparent_background'))
                        split = box.split(factor=0.4)
                        col = split.column(align=True)
                        col.label(text='')
                        split.operator('render.render', text=i18n.t('render'), icon='RENDER_STILL')
        bn_icon = 'HANDLETYPE_AUTO_CLAMP_VEC'
        if False:
            box = layout.box()
            box.operator('object.url_handler', text=i18n.t('how_to_use'), icon='HELP').rbx_link = 'Guide_Armature'
            icon = 'DOWNARROW_HLT' if context.scene.subpanel_bn_st1 else 'RIGHTARROW'
            box.prop(context.scene, 'subpanel_bn_st1', icon=icon, icon_only=False, text=i18n.t('step1_add_armature'))
            if context.scene.subpanel_bn_st1:
                bn_exist = 0
                try:
                    for i in bpy.context.selected_objects:
                        if i.type == 'ARMATURE':
                            bn_exist = 1
                            break
                except:
                    pass
                box.prop(rbx_prefs, 'rbx_arma_enum', text='')
                split = box.split(factor=0.5)
                col = split.column(align=True)
                col.label(text='')
                split.operator('object.button_bn', text=i18n.t('add_armature')).bn = 'arma'
                if bn_exist == 1:
                    split = box.split(factor=0.5)
                    col = split.column(align=True)
                    col.label(text=i18n.t('show_bones'))
                    split.prop(context.object, 'show_in_front')
                box.label(text='          -------------------------------------  ')
                box.label(text=i18n.t('you_may_try_from_step4'))
                box.label(text=i18n.t('if_no_work_back_to_step2'))
            box = layout.box()
            box.label(text=i18n.t('step2_prepare_mesh'), icon=bn_icon)
            box.operator('object.button_bn', text=i18n.t('recalculate_normals'), icon='NORMALS_FACE').bn = 'normal'
            if glob_vars.msh_selection:
                box.label(text=glob_vars.msh_selection, icon='ERROR')
            if glob_vars.msh_error == 'done_nml':
                box.label(text=i18n.t('recalucalting_done'), icon='CHECKMARK')
            box = layout.box()
            box.label(text=i18n.t('step3_double_vertices'), icon=bn_icon)
            msh_exist = 0
            dbls_msg = None
            try:
                if len(bpy.context.selected_objects) != 1:
                    dbls_msg = 'Select 1 Object'
                elif bpy.context.selected_objects[0].type != 'MESH':
                    dbls_msg = 'Object Must be a Mesh'
                else:
                    msh_exist = 1
                    dbls_msg = None
            except:
                pass
            if msh_exist == 1:
                try:
                    me = bpy.context.object.data
                except:
                    pass
                else:
                    dbls_msg = None
                    distance = 0.0001
                    bm = bmesh.new()
                    bm.from_mesh(me)
                    len_bef = len(bm.verts)
                    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance)
                    len_af = len(bm.verts)
                    doubles = len_bef - len_af
                    bm.clear()
                    bm.free()
                    box.label(text='Doubles Found: ' + str(doubles), icon='INFO')
            if dbls_msg:
                box.label(text=dbls_msg, icon='ERROR')
                box.label(text=i18n.t('doubles_found_error'), icon='INFO')
            box.operator('object.button_bn', text=i18n.t('remove_double_vertices'), icon='VERTEXSEL').bn = 'doubles'
            if glob_vars.msh_selection:
                box.label(text=glob_vars.msh_selection, icon='ERROR')
            if glob_vars.msh_error == 'done_vts':
                box.label(text=i18n.t('remove_doubles_done'), icon='CHECKMARK')
            msh_exist = 0
            try:
                for i in bpy.context.selected_objects:
                    if i.type == 'MESH':
                        msh_exist = 1
                        break
            except:
                pass
            if msh_exist == 1:
                box.label(text=i18n.t('optional_might_help_look_better'))
                split = box.split(factor=0.6)
                col = split.column(align=True)
                col.label(text=i18n.t('mesh_smoothing'))
                try:
                    if glob_vars.is_blender_version_below(4, 1):
                        split.prop(context.object.data, 'use_auto_smooth', text=i18n.t('auto'))
                    else:
                        split.operator('object.shade_auto_smooth', text=i18n.t('auto_smooth'))
                except:
                    pass
            box = layout.box()
            box.label(text=i18n.t('step4'), icon=bn_icon)
            box.label(text="Adjust Bones in 'Edit Mode'")
            box.label(text=i18n.t('if_needed'))
            box = layout.box()
            box.label(text=i18n.t('step5'), icon=bn_icon)
            box.label(text=i18n.t('select_mesh_bones_then_parent'))
            box.operator('object.button_bn', text=i18n.t('parent_bones_and_mesh'), icon='BONE_DATA').bn = 'parent'
            if glob_vars.bn_selection:
                box.label(text=glob_vars.bn_selection, icon='ERROR')
            if glob_vars.bn_error:
                if glob_vars.bn_error == 1:
                    box.label(text=i18n.t('error_need_rectify_mesh'), icon='ERROR')
                    glob_vars.bn_error = None
                if glob_vars.bn_error == 2:
                    glob_vars.bn_error = None
                    box.label(text=i18n.t('parenting_done'), icon='CHECKMARK')
                    box.label(text=i18n.t('step6_optional'), icon=bn_icon)
                    box.label(text=i18n.t('you_can_also_now_export_this'))
                    box.label(text=i18n.t('model_as_fbx_to_mixamo_for'))
                    box.label(text=i18n.t('animation_no_need_redo_bones'))
                    box.operator('object.url_handler', text=i18n.t('go_to_mixamo'), icon='URL').rbx_link = 'mixamo'
        row = layout.row()
        row = layout.row()
        row = layout.row()
        if rbx.is_logged_in:
            row = layout.row()
            icon = 'DOWNARROW_HLT' if context.scene.subpanel_upload else 'RIGHTARROW'
            row.prop(context.scene, 'subpanel_upload', icon=icon, icon_only=True)
            row.label(text=i18n.t('upload_to_roblox'), icon='COLLAPSEMENU')
            if context.scene.subpanel_upload:
                upload_section_box = layout.box()
                upload_section_box.prop(rbx, 'creator')
                if not rbx.is_processing_login_or_logout:
                    from oauth.lib.upload_operator import RBX_OT_upload
                    upload_section_box.row().operator(RBX_OT_upload.bl_idname)
                    # Allow user to apply a local skin image to selected mesh(es)
                    upload_section_box.row().operator('object.rbx_upload_skin', text=i18n.t('upload_skin'), icon='IMAGE_DATA')
                    # Skin preview and mapping options
                    img_name = getattr(scene, 'rbx_skin_last_image', '')
                    img = bpy.data.images.get(img_name) if img_name else None
                    if img:
                        try:
                            img.preview_ensure()
                        except Exception:
                            pass
                        upload_section_box.template_preview(img, show_buttons=False)
                    upload_section_box.prop(scene, 'rbx_skin_use_mapping', text=i18n.t('use_uv_mapping'))
                    if scene.rbx_skin_use_mapping:
                        upload_section_box.prop(scene, 'rbx_skin_uv_scale', text=i18n.t('uv_scale'))
                        upload_section_box.prop(scene, 'rbx_skin_uv_offset', text=i18n.t('uv_offset'))
                    # Target material selector for active mesh
                    if context.active_object and context.active_object.type == 'MESH':
                        try:
                            upload_section_box.prop_search(context.active_object, 'active_material', bpy.data, 'materials', text=i18n.t('target_material'))
                        except Exception:
                            pass
                        try:
                            upload_section_box.prop(context.active_object.data.uv_layers, 'active_index', text=i18n.t('uv_map'))
                        except Exception:
                            pass

                    human_models_box = upload_section_box.box()
                    human_models_box.label(text="Human models", icon="ARMATURE_DATA")
                    human_models = _get_human_model_candidates(scene)
                    if human_models:
                        for human_model in human_models:
                            row = human_models_box.row()
                            row.label(text=human_model.name, icon="ARMATURE_DATA")
                            op = row.operator("rbx.upload_single", text="Upload", icon="EXPORT")
                            op.target_object_name = human_model.name
                    else:
                        human_models_box.label(text="No human models found", icon="INFO")
                else:
                    upload_section_box.label(text=i18n.t('refreshing_login_please_wait'), icon='ERROR')
                from oauth.lib.get_selected_objects import get_selected_objects
                selected_text = ', '.join((obj.name for obj in get_selected_objects(context)))
                if selected_text:
                    upload_section_box.row().label(text=i18n.t('selected_objects'), icon='RESTRICT_SELECT_OFF')
                    selected_objects_display_box = upload_section_box.box()
                    selected_objects_display_box.label(text=selected_text)
                from oauth.lib import status_indicators
                status_indicators.draw_statuses(context.window_manager, upload_section_box)
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_other else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_other', icon=icon, icon_only=True)
        row.label(text=i18n.t('quick_functions'), icon='COLLAPSEMENU')
        if context.scene.subpanel_other:
            box = layout.box()
            objs = None
            mat = None
            try:
                objs = bpy.context.selected_objects
                try:
                    mat = bpy.context.object.active_material
                except:
                    pass
            except:
                pass
            if objs:
                if len(objs) == 1:
                    if mat:
                        box.label(text=i18n.t('culling_option'), icon='HIDE_ON')
                        box.label(text=i18n.t('hide_flipped_faces_like_in_roblox'))
                        box.prop(bpy.context.object.active_material, 'use_backface_culling', text=i18n.t('backface_culling'), icon='FACESEL')
                    else:
                        box.enabled = False
                        box.label(text=i18n.t('culling_option_add_material'), icon='HIDE_ON')
                        box.label(text=i18n.t('hide_flipped_faces_like_in_roblox'))
                        box.operator('object.rbx_button_of', text=i18n.t('backface_culling'), icon='FACESEL')
                else:
                    box.enabled = False
                    box.label(text=i18n.t('culling_option_select_1_object'), icon='HIDE_ON')
                    box.label(text=i18n.t('hide_flipped_faces_like_in_roblox'))
                    box.operator('object.rbx_button_of', text=i18n.t('backface_culling'), icon='FACESEL')
            else:
                box.enabled = False
                box.label(text=i18n.t('culling_option_select_object'), icon='HIDE_ON')
                box.label(text=i18n.t('hide_flipped_faces_like_in_roblox'))
                box.operator('object.rbx_button_of', text=i18n.t('backface_culling'), icon='FACESEL')
            box = layout.box()
            box.label(text=i18n.t('normals'), icon='ORIENTATION_NORMAL')
            box.prop(bpy.context.space_data.overlay, 'show_face_orientation', text=i18n.t('show_face_orientation'), icon='NORMALS_FACE')
            box.prop(rbx_prefs, 'rbx_face_enum')
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.operator('object.rbx_button_of', text=i18n.t('recalc_outside')).rbx_of = 'outside'
            split.operator('object.rbx_button_of', text=i18n.t('recalc_inside')).rbx_of = 'inside'
            box.operator('object.rbx_button_of', text=i18n.t('flip_normals')).rbx_of = 'flip'
            box = layout.box()
            try:
                if len(bpy.context.selected_objects) == 1:
                    box.label(text=i18n.t('glowing_ugc'), icon='SHADING_SOLID')
                    box.operator('object.rbx_button_of', text=i18n.t('make_item_glow')).rbx_of = 'glow'
                    box.operator('object.rbx_button_of', text=i18n.t('remove_glowing')).rbx_of = 'unglow'
                else:
                    box.enabled = False
                    box.label(text=i18n.t('glowing_ugc_select_object'), icon='SHADING_SOLID')
                    box.operator('object.rbx_button_of', text=i18n.t('make_item_glow')).rbx_of = 'glow'
                    box.operator('object.rbx_button_of', text=i18n.t('remove_glowing')).rbx_of = 'unglow'
            except:
                pass
            box = layout.box()
            if objs:
                if len(objs) == 1:
                    if mat:
                        box.label(text='UGC Outline ', icon='HIDE_ON')
                        box.operator('object.rbx_button_of', text=i18n.t('make_outline')).rbx_of = 'make_outline'
                        if 'RBX_Outline_mat' in objs[0].material_slots and 'RBX_Outline' in objs[0].modifiers:
                            mat = bpy.data.materials.get('RBX_Outline_mat')
                            color = mat.node_tree.nodes['RGB']
                            box.label(text=i18n.t('outline_controls'))
                            col_0 = color.outputs[0]
                            split = box.split(factor=0.5)
                            col = split.column(align=True)
                            col.label(text=i18n.t('preview_color'))
                            split.prop(col_0, 'default_value', text='')
                            box.prop(bpy.context.object.modifiers['RBX_Outline'], 'thickness', text=i18n.t('outline_thickness'))
                            box.label(text='')
                            box.label(text=i18n.t('add_outline_to_ugc'))
                            box.operator('object.rbx_button_of', text=i18n.t('apply_outline')).rbx_of = 'apply_outline'
                            box.label(text=i18n.t('outline_faces_will_be_added_to_your'))
                            box.label(text=i18n.t('object_and_uv_moved_outside'))
                            box.label(text=i18n.t('just_move_that_uv_to_the_color'))
                            box.label(text=i18n.t('that_you_need_or_reunwrap_it'))
                    else:
                        box.enabled = False
                        box.label(text=i18n.t('ugc_outline_add_material'), icon='HIDE_ON')
                        box.operator('object.rbx_button_of', text=i18n.t('make_outline')).rbx_of = 'make_outline'
                else:
                    box.enabled = False
                    box.label(text=i18n.t('ugc_outline_select_1_object'), icon='HIDE_ON')
                    box.operator('object.rbx_button_of', text=i18n.t('make_outline')).rbx_of = 'make_outline'
            else:
                box.enabled = False
                box.label(text=i18n.t('ugc_outline_select_object'), icon='HIDE_ON')
                box.operator('object.rbx_button_of', text=i18n.t('make_outline')).rbx_of = 'make_outline'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_export else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_export', icon=icon, icon_only=True)
        row.label(text=i18n.t('file_export'), icon='COLLAPSEMENU')
        if context.scene.subpanel_export:
            row = layout.row()
            row = layout.row()
            box = layout.box()
            box.label(text=i18n.t('ugc_item_export'))
            is_valid_ugc = False
            if len(context.selected_objects) == 1:
                obj = context.selected_objects[0]
                if obj.type == 'MESH':
                    is_valid_ugc = True
            try:
                if is_valid_ugc:
                    box.prop(rbx_prefs, 'rbx_of_orig', text=i18n.t('set_origin_to_geometry'))
                    box.prop(rbx_prefs, 'rbx_of_trsf', text=i18n.t('apply_all_transforms'))
                    box.operator('object.rbx_operators', text=i18n.t('export_fbx'), icon='EXPORT').rbx_operator = 'exp_fbx'
                else:
                    box.label(text=i18n.t('select_1_mesh_for_fbx_export'), icon='ERROR')
            except:
                box.label(text=i18n.t('select_1_mesh_for_fbx_export'), icon='ERROR')
            row = layout.row()
            box = layout.box()
            box.label(text=i18n.t('layered_cloth_export'))
            box.label(text=i18n.t('make_sure_you_select_these'))
            box.label(text=i18n.t('1_armature'))
            box.label(text=i18n.t('2_youritem_in_armature'))
            box.label(text=i18n.t('3_itemname_outercage'))
            box.label(text=i18n.t('4_itemname_innercage'))
            try:
                if len(bpy.context.selected_objects) >= 4:
                    box.operator('object.rbx_operators', text=i18n.t('export_fbx'), icon='EXPORT').rbx_operator = 'exp_fbx_lc'
                else:
                    box.label(text=i18n.t('some_items_not_selected'), icon='ERROR')
            except:
                box.label(text=i18n.t('some_items_not_selected'), icon='ERROR')
            row = layout.row()
            box = layout.box()
            box.label(text=i18n.t('animation_export'))
            is_valid_anim_rig = False
            active_obj = context.active_object
            if active_obj and active_obj.type == 'ARMATURE':
                if active_obj.animation_data and active_obj.animation_data.action:
                    is_valid_anim_rig = True
            row_op = box.row()
            row_op.enabled = is_valid_anim_rig
            row_op.operator('object.rbx_operators', text=i18n.t('export_animation'), icon='ACTION').rbx_operator = 'exp_fbx_anim'
            if not is_valid_anim_rig:
                box.label(text=i18n.t('select_armature_with_animation'), icon='INFO')
            row = layout.row()
            box = layout.box()
            box.label(text=i18n.t('avatar_export'))
            box.label(text=i18n.t('select_all_parts_1st'))
            box.operator('object.rbx_button_ava', text=i18n.t('export_avatar')).rbx_ava = 'export'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_pie else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_pie', icon=icon, icon_only=True)
        row.label(text=i18n.t('pie_menu'), icon='COLLAPSEMENU')
        if context.scene.subpanel_pie:
            box = layout.box()
            box.operator_context = 'INVOKE_DEFAULT' if True else 'EXEC_DEFAULT'
            split = box.split(factor=0.5)
            col = split.column(align=True)
            col.label(text=i18n.t('shortcut'), icon_value=672)
            try:
                split.prop(menu_pie.find_user_keyconfig('F85A6'), 'type', text='', full_event=True)
            except:
                split.label(text=i18n.t('shortcut_not_found'))
            box.label(text=i18n.t('1_wont_work_if_shortcut_exist'))
            box.label(text=i18n.t('2_work_in_obj_mode_only'))
        row = layout.row()
        row.label(text='          -------------------------------------  ')
        row = layout.row()
        row.operator('object.rbx_button_of', text=i18n.t('install_cool_theme'), icon='BRUSHES_ALL').rbx_of = 'theme_install'
        row = layout.row()
        row.operator('object.url_handler', text=i18n.t('discord_support_server'), icon='URL').rbx_link = 'discord'
        row = layout.row()
        row.operator('object.url_handler', text=i18n.t('buy_me_a_coffee'), icon='URL').rbx_link = 'buy coffee'
        row = layout.row()
        icon = 'DOWNARROW_HLT' if context.scene.subpanel_support else 'RIGHTARROW'
        row.prop(context.scene, 'subpanel_support', icon=icon, icon_only=True)
        row.label(text=i18n.t('support_with_robux'), icon='FUND')
        if context.scene.subpanel_support:
            box = layout.box()
            split_sup = box.split(factor=0.2)
            col_sup = split_sup.column(align=True)
            col_sup.label(text='', icon='LAYERGROUP_COLOR_04')
            split_sup.operator('object.url_handler', text=i18n.t('supporter_10_bobuc')).rbx_link = 'tips 10'
            split_sup = box.split(factor=0.2)
            col_sup = split_sup.column(align=True)
            col_sup.label(text='', icon='LAYERGROUP_COLOR_03')
            split_sup.operator('object.url_handler', text=i18n.t('hero_50_bobuc')).rbx_link = 'tips 50'
            split_sup = box.split(factor=0.2)
            col_sup = split_sup.column(align=True)
            col_sup.label(text='', icon='LAYERGROUP_COLOR_06')
            split_sup.operator('object.url_handler', text=i18n.t('legend_500_bobuc')).rbx_link = 'tips 500'
            split_sup = box.split(factor=0.2)
            col_sup = split_sup.column(align=True)
            col_sup.label(text='', icon='LAYERGROUP_COLOR_07')
            split_sup.operator('object.url_handler', text=i18n.t('epic_1000_bobuc')).rbx_link = 'tips 1000'