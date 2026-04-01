import bpy
import os
import asyncio
import requests
import json
import importlib
from test321 import glob_vars, i18n
from glob_vars import addon_path
from typing import TYPE_CHECKING
from test321 import i18n
if TYPE_CHECKING:
    from rbx_import_discovery import *
DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs) if DEBUG else None
category_checkboxes = {'Body Parts': ['rbx_enum_body_parts'], 'Accessory': [], 'Dynamic Head': ['rbx_enum_dynamic_head'], 'Layered Cloth': ['rbx_enum_layered_cloth', 'rbx_bnds_lc_enum', 'rbx_lc_dum_enum', 'rbx_lc_spl_enum', 'rbx_lc_dum_anim_enum', 'rbx_lc_anim_enum'], 'Face Parts': ['rbx_enum_face_parts', 'rbx_bnds_lc_enum', 'rbx_lc_dum_enum', 'rbx_lc_spl_enum', 'rbx_lc_dum_anim_enum', 'rbx_lc_anim_enum'], 'Classics': ['rbx_enum_classics'], 'Gear': ['rbx_enum_gear'], 'Armature': [], 'Store Model': [], 'Models': []}

class RBX_OT_import_discovery(bpy.types.Operator):
    """Asset Discovery"""
    bl_idname = 'object.rbx_import_discovery'
    bl_label = i18n.t('asset_discovery')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        glob_vars.rbx_imp_error = None
        from .readers import mesh_reader
        importlib.reload(mesh_reader)
        from . import func_rbx_other
        importlib.reload(func_rbx_other)
        from . import func_rbx_cloud_api
        importlib.reload(func_rbx_cloud_api)
        from . import func_rbx_api
        importlib.reload(func_rbx_api)
        from . import rbx_import_download_manager
        importlib.reload(rbx_import_download_manager)
        from . import rbx_import_meshes
        importlib.reload(rbx_import_meshes)
        from . import rbx_import_cages
        importlib.reload(rbx_import_cages)
        from . import rbx_import_attachments
        importlib.reload(rbx_import_attachments)
        context.scene.rbx_prefs.rbx_import_beta_active = True
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        access_token = loop.run_until_complete(func_rbx_other.renew_token(context))
        headers = {'Authorization': f'Bearer {access_token}'}
        rbx_prefs = context.scene.rbx_prefs
        rbx_item_field_entry = rbx_prefs.rbx_item_field_entry
        (rbx_asset_id, rbx_imp_error) = func_rbx_other.item_field_extract_id(rbx_item_field_entry)
        if rbx_imp_error:
            self.report({'ERROR'}, rbx_imp_error)
            return {'CANCELLED'}
        dprint(f'Asset Discovery started for ID: {rbx_asset_id}')
        if not rbx_imp_error:
            (rbx_asset_name, rbx_asset_type_id, rbx_asset_creator, rbx_bundledItems, rbx_imp_error) = func_rbx_api.get_catalog_bundle_data(rbx_asset_id, headers)
            if rbx_imp_error:
                inStr = str(rbx_imp_error)
                if '404' in inStr:
                    dprint('Bundle not found, trying as Single Asset...')
                    (asset_name, asset_type_id, asset_creator, asset_error) = func_rbx_api.get_catalog_asset_data(rbx_asset_id, headers)
                    if asset_name:
                        dprint(f'Found Single Asset: {asset_name} (Type: {asset_type_id})')
                        rbx_imp_error = None
                        glob_vars.rbx_imp_error = None
                        rbx_asset_name = asset_name
                        rbx_asset_type_id = asset_type_id
                        rbx_asset_creator = asset_creator
                        rbx_bundledItems = [{'id': int(rbx_asset_id), 'name': rbx_asset_name, 'type': 'Asset', 'assetType': asset_type_id}]
                    else:
                        dprint('Single Asset check failed:', asset_error)
                        if '429' not in str(asset_error):
                            self.report({'ERROR'}, f'Discovery Failed: {asset_error}')
                        return {'CANCELLED'}
                else:
                    if '429' not in str(rbx_imp_error):
                        self.report({'ERROR'}, f'Bundle Discovery Failed: {rbx_imp_error}')
                    return {'CANCELLED'}
            dprint('rbx_bundledItems: ', rbx_bundledItems)
            glob_vars.rbx_asset_name = rbx_asset_name
            glob_vars.rbx_asset_creator = rbx_asset_creator
            glob_vars.rbx_asset_id = int(rbx_asset_id)
            type_name = glob_vars.rbx_bundle_types.get(rbx_asset_type_id)
            if not type_name:
                type_name = glob_vars.rbx_asset_types.get(rbx_asset_type_id, f'Unknown Type ({rbx_asset_type_id})')
            glob_vars.rbx_asset_type = type_name
            glob_vars.discovered_items_data = {cat: [] for cat in glob_vars.supported_assets_v2}
            glob_vars.rbx_default_head_used = False
            if rbx_bundledItems:
                for item in rbx_bundledItems:
                    if item.get('type') == 'Asset':
                        asset_type = item.get('assetType')
                        for (category, types) in glob_vars.supported_assets_v2.items():
                            if asset_type in types:
                                if category == 'Animations':
                                    if rbx_asset_type_id is not None and rbx_asset_type_id != 2 and (rbx_asset_type_id != 'Animation'):
                                        break
                                glob_vars.discovered_items_data[category].append({'id': item.get('id'), 'name': item.get('name')})
                                break
            if rbx_asset_type_id == 1 and (not glob_vars.discovered_items_data.get('Dynamic Head')):
                dprint('No Dynamic Head found for Character Bundle. Adding Default (ID 10687288296).')
                glob_vars.discovered_items_data['Dynamic Head'].append({'id': 10687288296, 'name': 'Dylan Standard (Default)'})
                glob_vars.rbx_default_head_used = True
            dprint('Grouped Items:', glob_vars.discovered_items_data)
            has_discovered = any((items for items in glob_vars.discovered_items_data.values()))
            if not has_discovered:
                type_name = glob_vars.rbx_asset_types.get(rbx_asset_type_id, f'Type {rbx_asset_type_id}')
                glob_vars.rbx_imp_error = f'Asset Type:{rbx_asset_type_id} ({type_name}) Not supported'
                dprint(f'Unsupported asset type: {type_name} ({rbx_asset_type_id})')
            rbx_asset_name_clean = func_rbx_other.replace_restricted_char(rbx_asset_name)
            glob_vars.rbx_asset_name_clean = rbx_asset_name_clean
            is_bundle = rbx_asset_type_id in glob_vars.rbx_bundle_types.keys()
            if len(rbx_bundledItems) == 1 and rbx_bundledItems[0]['id'] == int(rbx_asset_id):
                pass
            (img_url, img_error) = func_rbx_api.get_asset_and_bundle_img_url(rbx_asset_id, is_bundle)
            if not img_error and img_url:
                (img_data, img_error) = func_rbx_api.get_asset_and_bundle_img(img_url)
                if not img_error and img_data:
                    try:
                        old_img = bpy.data.images.get(rbx_asset_name_clean + '.png')
                        if old_img:
                            bpy.data.images.remove(old_img)
                        tmp_dir = os.path.join(glob_vars.addon_path, glob_vars.rbx_import_main_folder, 'tmp')
                        if not os.path.exists(tmp_dir):
                            os.makedirs(tmp_dir)
                        img_path = os.path.join(tmp_dir, rbx_asset_name_clean + '.png')
                        with open(img_path, 'wb') as f:
                            f.write(img_data)
                        bpy.data.images.load(img_path)
                        dprint(f'Thumbnail loaded: {img_path}')
                    except Exception as e:
                        dprint(f'Error saving/loading thumbnail: {e}')
                else:
                    dprint(f'Error getting image data: {img_error}')
            else:
                dprint(f'Error getting image URL: {img_error}')
        return {'FINISHED'}

class RBX_OT_import_reset(bpy.types.Operator):
    """Reset Import (Beta)"""
    bl_idname = 'object.rbx_import_reset'
    bl_label = i18n.t('reset')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        glob_vars.rbx_imp_error = None
        rbx_prefs = context.scene.rbx_prefs
        rbx_prefs.rbx_import_beta_active = False
        glob_vars.discovered_items_data = {}
        glob_vars.rbx_default_head_used = False
        glob_vars.rbx_armature_warning_active = False
        glob_vars.rbx_anim_sub_items = []
        self.report({'INFO'}, i18n.t('import_beta_reset'))
        return {'FINISHED'}

class RBX_OT_import_discovery_download(bpy.types.Operator):
    """Download Discovered Items"""
    bl_idname = 'object.rbx_import_discovery_download'
    bl_label = i18n.t('download')
    bl_options = {'REGISTER', 'UNDO'}
    category: bpy.props.StringProperty()

    def execute(self, context):
        self.report({'INFO'}, i18n.t('download_triggered_for_category_selfcate', self=self))
        from . import rbx_import_download_manager
        importlib.reload(rbx_import_download_manager)
        glob_vars.rbx_armature_warning_active = False
        download_all_items = self.category == 'ALL_CATEGORIES'
        if self.category == 'Body Parts' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_body_parts'))
            rbx_import_download_manager.download_body_parts(context, category_name='Body Parts', download_all=download_all_items)
        if self.category == 'Dynamic Head' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_dynamic_heads'))
            rbx_import_download_manager.download_body_parts(context, category_name='Dynamic Head', download_all=download_all_items)
        if self.category == 'Accessory' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_accessories'))
            rbx_import_download_manager.download_body_parts(context, category_name='Accessory', download_all=download_all_items)
        if self.category == 'Layered Cloth' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_layered_cloth'))
            rbx_import_download_manager.download_body_parts(context, category_name='Layered Cloth', download_all=download_all_items)
        if self.category == 'Face Parts' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_face_parts'))
            rbx_import_download_manager.download_body_parts(context, category_name='Face Parts', download_all=download_all_items)
        if self.category == 'Classics' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_classics'))
            rbx_import_download_manager.download_body_parts(context, category_name='Classics', download_all=download_all_items)
        if self.category == 'Gear' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_gears'))
            rbx_import_download_manager.download_body_parts(context, category_name='Gear', download_all=download_all_items)
        if self.category == 'Armature' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_armature'))
            rbx_import_download_manager.download_body_parts(context, category_name='Armature', download_all=download_all_items)
        if self.category == 'Animations':
            self.report({'INFO'}, i18n.t('downloading_animations'))
            rbx_import_download_manager.download_animation(context)
        if self.category == 'Models' or self.category == 'ALL_CATEGORIES':
            self.report({'INFO'}, i18n.t('downloading_models'))
            rbx_import_download_manager.download_model(context, download_all=download_all_items)
        if self.category.startswith('Animations_Apply_'):
            anim_idx = int(self.category.split('_')[-1])
            self.report({'INFO'}, i18n.t('applying_animation'))
            rbx_import_download_manager.download_animation(context, apply_index=anim_idx)
        rbx_import_download_manager.execute_global_spawn_tracker()
        from . import func_blndr_api
        importlib.reload(func_blndr_api)
        func_blndr_api.blender_api_collapse_outliner()
        return {'FINISHED'}

class RBX_OT_import_discovery_options(bpy.types.Operator):
    """Configuration Options for Discovery Category"""
    bl_idname = 'object.rbx_import_discovery_options'
    bl_label = i18n.t('options')
    bl_options = {'REGISTER', 'UNDO'}
    category: bpy.props.StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        rbx_prefs = context.scene.rbx_prefs
        category = self.category
        box = layout.box()
        box.label(text=i18n.t('options_category', category=category), icon='PREFERENCES')
        if category == 'Body Parts':
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_at_origin')
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_add_meshes')
            row = box.row()
            row.enabled = rbx_prefs.rbx_bndl_char_choice_add_meshes
            row.prop(rbx_prefs, 'rbx_bndl_char_choice_add_textures')
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_add_cages')
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_add_attachment')
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_add_motor6d_attachment')
            row = box.row()
            row.enabled = rbx_prefs.rbx_bndl_char_choice_add_meshes or rbx_prefs.rbx_bndl_char_choice_add_cages
            row.prop(rbx_prefs, 'rbx_bndl_char_choice_add_ver_col')
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_clean_tmp_meshes')
        if category == 'Dynamic Head':
            box.prop(rbx_prefs, 'rbx_dyn_heads_choice_at_origin')
            box.prop(rbx_prefs, 'rbx_dyn_heads_choice_add_meshes')
            row = box.row()
            row.enabled = rbx_prefs.rbx_dyn_heads_choice_add_meshes
            row.prop(rbx_prefs, 'rbx_dyn_heads_choice_add_textures')
            box.prop(rbx_prefs, 'rbx_dyn_heads_choice_add_cages')
            box.prop(rbx_prefs, 'rbx_dyn_heads_choice_add_attachment')
            box.prop(rbx_prefs, 'rbx_dyn_heads_choice_add_motor6d_attachment')
            row = box.row()
            row.enabled = rbx_prefs.rbx_dyn_heads_choice_add_meshes or rbx_prefs.rbx_dyn_heads_choice_add_cages
            row.prop(rbx_prefs, 'rbx_dyn_heads_choice_add_ver_col')
            box.prop(rbx_prefs, 'rbx_dyn_heads_choice_clean_tmp_meshes')
        if category == 'Accessory':
            box.prop(rbx_prefs, 'rbx_accessory_choice_at_origin')
            box.prop(rbx_prefs, 'rbx_accessory_choice_add_meshes')
            row = box.row()
            row.enabled = rbx_prefs.rbx_accessory_choice_add_meshes
            row.prop(rbx_prefs, 'rbx_accessory_choice_add_textures')
            box.prop(rbx_prefs, 'rbx_accessory_choice_add_attachment')
            row = box.row()
            row.enabled = rbx_prefs.rbx_accessory_choice_add_attachment
            row = box.row()
            row.enabled = rbx_prefs.rbx_accessory_choice_add_meshes
            row.prop(rbx_prefs, 'rbx_accessory_choice_add_ver_col')
            box.prop(rbx_prefs, 'rbx_accessory_choice_clean_tmp_meshes')
        if category == 'Layered Cloth':
            box.prop(rbx_prefs, 'rbx_lc_choice_at_origin')
            box.prop(rbx_prefs, 'rbx_lc_choice_add_meshes')
            row = box.row()
            row.enabled = rbx_prefs.rbx_lc_choice_add_meshes
            row.prop(rbx_prefs, 'rbx_lc_choice_add_textures')
            box.prop(rbx_prefs, 'rbx_lc_choice_add_cages')
            box.prop(rbx_prefs, 'rbx_lc_choice_add_attachment')
            row = box.row()
            row.enabled = rbx_prefs.rbx_lc_choice_add_attachment
            row = box.row()
            row.enabled = rbx_prefs.rbx_lc_choice_add_meshes or rbx_prefs.rbx_lc_choice_add_cages
            row.prop(rbx_prefs, 'rbx_lc_choice_add_ver_col')
            box.prop(rbx_prefs, 'rbx_lc_choice_clean_tmp_meshes')
        if category == 'Face Parts':
            box.prop(rbx_prefs, 'rbx_fp_choice_at_origin')
            box.prop(rbx_prefs, 'rbx_fp_choice_add_meshes')
            row = box.row()
            row.enabled = rbx_prefs.rbx_fp_choice_add_meshes
            row.prop(rbx_prefs, 'rbx_fp_choice_add_textures')
            box.prop(rbx_prefs, 'rbx_fp_choice_add_cages')
            box.prop(rbx_prefs, 'rbx_fp_choice_add_attachment')
            row = box.row()
            row.enabled = rbx_prefs.rbx_fp_choice_add_attachment
            row = box.row()
            row.enabled = rbx_prefs.rbx_fp_choice_add_meshes or rbx_prefs.rbx_fp_choice_add_cages
            row.prop(rbx_prefs, 'rbx_fp_choice_add_ver_col')
            box.prop(rbx_prefs, 'rbx_fp_choice_clean_tmp_meshes')
        if category == 'Gear':
            box.prop(rbx_prefs, 'rbx_gears_choice_at_origin')
            box.prop(rbx_prefs, 'rbx_gears_choice_add_meshes')
            row = box.row()
            row.enabled = rbx_prefs.rbx_gears_choice_add_meshes
            row.prop(rbx_prefs, 'rbx_gears_choice_add_textures')
            box.prop(rbx_prefs, 'rbx_gears_choice_clean_tmp_meshes')
        if category == 'Armature':
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_armature_at_origin')
            box.prop(rbx_prefs, 'rbx_bndl_char_choice_armature_link_meshes')
        if category == 'Models':
            box.prop(rbx_prefs, 'rbx_model_choice_at_origin')
            box.prop(rbx_prefs, 'rbx_model_choice_add_textures')
        if category in category_checkboxes:
            for prop_name in category_checkboxes[category]:
                if category == 'Body Parts':
                    continue
                if category in ['Layered Cloth', 'Face Parts']:
                    continue
                if category == 'Dynamic Head' and prop_name == 'rbx_enum_dynamic_head':
                    continue
                if category == 'Gear' and prop_name == 'rbx_enum_gear':
                    continue
                if hasattr(rbx_prefs, prop_name):
                    box.prop(rbx_prefs, prop_name)

    def execute(self, context):
        return {'FINISHED'}

class RBX_OT_import_discovery_open_folder(bpy.types.Operator):
    """Open Import Folder"""
    bl_idname = 'object.rbx_import_discovery_open_folder'
    bl_label = i18n.t('open_folder')
    bl_options = {'REGISTER', 'UNDO'}
    category: bpy.props.StringProperty()

    def execute(self, context):
        category = self.category
        target_subfolder = glob_vars.rbx_import_v2_bundles
        if category == 'Accessory':
            target_subfolder = 'Accessories'
        elif category == 'Gear':
            target_subfolder = 'Gears'
        elif category == 'Layered Cloth':
            target_subfolder = 'Layered Clothing'
        elif category == 'Dynamic Head':
            target_subfolder = 'Dynamic Heads'
        elif category == 'Face Parts':
            target_subfolder = 'Face Parts'
        elif category == 'Classics':
            target_subfolder = 'Classics'
        elif category == 'Armature':
            target_subfolder = glob_vars.rbx_import_v2_bundles
        elif category == 'Models':
            target_subfolder = 'Models'
        folder_path = os.path.join(addon_path, glob_vars.rbx_import_main_folder, target_subfolder)
        if folder_path:
            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path)
                    self.report({'INFO'}, i18n.t('created_folder_folder_path', folder_path=folder_path))
                except Exception as e:
                    self.report({'ERROR'}, i18n.t('could_not_create_folder_e', e=e))
                    return {'CANCELLED'}
            try:
                os.startfile(folder_path)
                self.report({'INFO'}, i18n.t('opened_folder_folder_path', folder_path=folder_path))
            except Exception as e:
                self.report({'ERROR'}, i18n.t('could_not_open_folder_e', e=e))
        else:
            self.report({'WARNING'}, i18n.t('no_folder_mapped_for_category_category', category=category))
        return {'FINISHED'}

class RBX_OT_import_discovery_info_popup(bpy.types.Operator):
    """Click Me"""
    bl_idname = 'object.rbx_import_discovery_info_popup'
    bl_label = i18n.t('info')
    bl_options = {'REGISTER', 'INTERNAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
        layout.label(text=i18n.t('info_2a72c335'), icon='INFO')
        layout.separator()
        box = layout.box()
        box.label(text=i18n.t('1_spawn_at_origin'))
        col = box.column(align=True)
        col.label(text=i18n.t('when_this_option_is_enabled_objects_will'))
        col.label(text=i18n.t('instead_of_being_placed_at_their_origina'))
        box = layout.box()
        box.label(text=i18n.t('2_incorrect_item_placement'))
        col = box.column(align=True)
        col.label(text=i18n.t('some_items_may_not_appear_in_their_expec'))
        col.label(text=i18n.t('because_the_item'))
        col.label(text=i18n.t('rbx_toolbox_reads_the_object'))
        box = layout.box()
        box.label(text=i18n.t('3_importing_items_separately'))
        col = box.column(align=True)
        col.label(text=i18n.t('if_you_import_items_individually_such_as'))
        col.label(text=i18n.t('they_may_not_be_placed_correctly_this_oc'))
        col.label(text=i18n.t('selection_to_the_origin_relative_to_the'))
        col.separator()
        col.label(text=i18n.t('if_you_disable_spawn_at_origin_the_items'))
        col.label(text=i18n.t('but_they_may_be_located_far_from_the_ble'))
        box = layout.box()
        box.label(text=i18n.t('4_exclude_from_import'))
        col = box.column(align=True)
        col.label(text=i18n.t('if_you_want_to_exclude_some_items_from_g'))
        col.label(text=i18n.t('deselect_all_checkboxes_in_the_item_opti'))

    def execute(self, context):
        return {'FINISHED'}

class RBX_OT_open_tmp_folder(bpy.types.Operator):
    """Open Junk (tmp) Folder"""
    bl_idname = 'object.rbx_open_tmp_folder'
    bl_label = i18n.t('open_junk_tmp_folder')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        folder_path = os.path.join(addon_path, glob_vars.rbx_import_main_folder, 'tmp_rbxm')
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except Exception as e:
                self.report({'ERROR'}, f'Could not create folder: {e}')
                return {'CANCELLED'}
        try:
            os.startfile(folder_path)
            self.report({'INFO'}, f'Opened folder: {folder_path}')
        except Exception as e:
            self.report({'ERROR'}, f'Could not open folder: {e}')
        return {'FINISHED'}

class RBX_OT_import_model_summary(bpy.types.Operator):
    """Import Summary Popup"""
    bl_idname = 'wm.rbx_import_model_summary'
    bl_label = i18n.t('import_summary')
    bl_options = {'REGISTER', 'INTERNAL'}
    imported_count: bpy.props.IntProperty(default=0)
    failed_permission: bpy.props.StringProperty(default='')
    failed_other: bpy.props.StringProperty(default='')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text=i18n.t('imported_selfimported_count_objects', self=self))
        perm = [p for p in self.failed_permission.split(',') if p]
        other = [o for o in self.failed_other.split(',') if o]
        if perm or other:
            layout.separator()
            box_failed = layout.box()
            box_failed.alert = True
            box_failed.label(text=i18n.t('failed_to_import'), icon='ERROR')
            if perm:
                col = box_failed.column(align=True)
                col.label(text=i18n.t('permission_denied'))
                for p in perm:
                    col.label(text=p)
            if other:
                if perm:
                    box_failed.separator()
                col = box_failed.column(align=True)
                col.label(text=i18n.t('other_error'))
                for o in other:
                    col.label(text=o)

    def execute(self, context):
        return {'FINISHED'}


class RBX_OT_import_avatar(bpy.types.Operator):
    """Import a Roblox avatar by username/ID or current login"""

    bl_idname = 'object.rbx_import_avatar'
    bl_label = 'Import Avatar'
    bl_options = {'REGISTER', 'UNDO'}

    source: bpy.props.StringProperty(default='USER_INPUT')

    def execute(self, context):
        glob_vars.rbx_imp_error = None
        from . import func_rbx_api, func_rbx_other
        importlib.reload(func_rbx_api)
        importlib.reload(func_rbx_other)

        rbx_prefs = context.scene.rbx_prefs
        username_or_id = rbx_prefs.rbx_username_entered
        glob_vars.rbx_avatar_rig_type = rbx_prefs.rbx_avatar_rig_type

        if self.source == 'SELF':
            login_info = glob_vars.get_login_info()
            username_or_id = login_info.get('user_id') or login_info.get('user_name')
            if not username_or_id:
                self.report({'ERROR'}, 'No logged-in user found')
                return {'CANCELLED'}

        user_id, user_id_error = func_rbx_api.get_user_id_from_username(username_or_id)
        if user_id_error:
            self.report({'ERROR'}, user_id_error)
            return {'CANCELLED'}

        assets, avatar_error = func_rbx_api.get_user_avatar_assets(user_id)
        if avatar_error:
            self.report({'ERROR'}, avatar_error)
            return {'CANCELLED'}

        if not assets:
            self.report({'ERROR'}, 'Avatar has no assets to import')
            return {'CANCELLED'}

        glob_vars.rbx_asset_name = f"Avatar_{user_id}"
        glob_vars.rbx_asset_creator = str(username_or_id)
        glob_vars.rbx_asset_id = int(user_id)
        glob_vars.rbx_asset_type = "Avatar"
        glob_vars.rbx_default_head_used = False
        glob_vars.rbx_asset_name_clean = func_rbx_other.replace_restricted_char(glob_vars.rbx_asset_name)
        glob_vars.discovered_items_data = {cat: [] for cat in glob_vars.supported_assets_v2}

        for asset in assets:
            asset_id = asset.get('id')
            asset_name = asset.get('name') or f"Asset {asset_id}"
            asset_type = asset.get('assetType', {})
            asset_type_id = asset_type.get('id')
            if not asset_id or not asset_type_id:
                continue

            for (category, types) in glob_vars.supported_assets_v2.items():
                if asset_type_id in types:
                    glob_vars.discovered_items_data[category].append({'id': asset_id, 'name': asset_name})
                    break

        has_discovered = any((items for items in glob_vars.discovered_items_data.values()))
        if not has_discovered:
            glob_vars.rbx_imp_error = 'Avatar asset types are not supported'
            self.report({'ERROR'}, glob_vars.rbx_imp_error)
            return {'CANCELLED'}

        rbx_prefs.rbx_import_beta_active = True
        return {'FINISHED'}