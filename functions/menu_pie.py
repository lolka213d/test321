import bpy
from test321 import glob_vars, i18n




#### RBX PIE MENU ####
def find_user_keyconfig(key):
    km, kmi = glob_vars.addon_keymaps[key]
    for item in bpy.context.window_manager.keyconfigs.user.keymaps[km.name].keymap_items:
        found_item = False
        if kmi.idname == item.idname:
            found_item = True
            for name in dir(kmi.properties):
                if not name in ["bl_rna", "rna_type"] and not name[0] == "_":
                    if not kmi.properties[name] == item.properties[name]:
                        found_item = False
        if found_item:
            return item
    print(f"Couldn't find keymap item for {key}, using addon keymap instead. This won't be saved across sessions!")
    return kmi


#### MAIN MENU ####
class RBX_MT_MENU(bpy.types.Menu):
    bl_idname = "RBX_MT_MENU"
    bl_label = i18n.t('rbx_toolbox_menu')

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        layout = self.layout.menu_pie()
        op = layout.prop(bpy.context.space_data.overlay, 'show_face_orientation', text=i18n.t('show_face_orientation'), icon='NORMALS_FACE') 
        layout.menu('RBX_MT_MENU3', text=i18n.t('set_origin'), icon='LAYER_ACTIVE')
        layout.menu('RBX_MT_MENU2', text=i18n.t('recalculate_normals'), icon='FACESEL')
        layout.menu('RBX_MT_MENU4', text=i18n.t('shading'), icon='SHADING_TEXTURE')
        

           
#### Recalculate MENU ####        
class RBX_MT_MENU2(bpy.types.Menu):
    bl_idname = "RBX_MT_MENU2"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        layout = self.layout.column_flow(columns=1)
        layout.operator_context = "INVOKE_DEFAULT"
        layout.menu('RBX_MT_MENU2_1', text=i18n.t('recalc_outside'), icon_value=0)
        layout.menu('RBX_MT_MENU2_2', text=i18n.t('recalc_inside'), icon_value=0)
        layout.menu('RBX_MT_MENU2_3', text=i18n.t('flip_normals'), icon_value=0)


#### Recalculate SUBMENU Recalc Outside ####        
class RBX_MT_MENU2_1(bpy.types.Menu):
    bl_idname = "RBX_MT_MENU2_1"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        layout = self.layout.column_flow(columns=1)
        layout.operator_context = "INVOKE_DEFAULT"
        op = layout.operator("object.rbx_button_of", text = i18n.t('all_faces')).rbx_of = 'pie_outside_all'
        op = layout.operator("object.rbx_button_of", text = i18n.t('selected_faces')).rbx_of = 'pie_outside'


#### Recalculate SUBMENU Recalc Inside ####        
class RBX_MT_MENU2_2(bpy.types.Menu):
    bl_idname = "RBX_MT_MENU2_2"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        layout = self.layout.column_flow(columns=1)
        layout.operator_context = "INVOKE_DEFAULT"
        op = layout.operator("object.rbx_button_of", text = i18n.t('all_faces')).rbx_of = 'pie_inside_all'
        op = layout.operator("object.rbx_button_of", text = i18n.t('selected_faces')).rbx_of = 'pie_inside'
        

#### Recalculate SUBMENU Recalc Flip Normals ####        
class RBX_MT_MENU2_3(bpy.types.Menu):
    bl_idname = "RBX_MT_MENU2_3"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        layout = self.layout.column_flow(columns=1)
        layout.operator_context = "INVOKE_DEFAULT"
        op = layout.operator("object.rbx_button_of", text = i18n.t('all_faces')).rbx_of = 'pie_flip_all'
        op = layout.operator("object.rbx_button_of", text = i18n.t('selected_faces')).rbx_of = 'pie_flip'
        

#### Origin MENU #### 
class RBX_MT_MENU3(bpy.types.Menu):
    bl_idname = "RBX_MT_MENU3"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        layout = self.layout.column_flow(columns=1)
        layout.operator_context = "INVOKE_DEFAULT"
        op = layout.operator("object.rbx_button_of", text = i18n.t('to_geometry')).rbx_of = 'orig_to_geo'
        op = layout.operator("object.rbx_button_of", text = i18n.t('to_3d_cursor')).rbx_of = 'orig_to_3d'

        
#### Shading MENU #### 
class RBX_MT_MENU4(bpy.types.Menu):
    bl_idname = "RBX_MT_MENU4"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        layout = self.layout.column_flow(columns=1)
        layout.operator_context = "INVOKE_DEFAULT"
        op = layout.operator("object.rbx_button_of", text = i18n.t('shade_flat')).rbx_of = 'shd_flat'
        op = layout.operator("object.rbx_button_of", text = i18n.t('shade_smooth')).rbx_of = 'shd_smooth'
        op = layout.operator("object.rbx_button_of", text = i18n.t('shade_auto_smooth')).rbx_of = 'shd_aut_smooth'
        #op = layout.prop(bpy.context.object.data.auto_smooth_angle,"default_value", text = "")