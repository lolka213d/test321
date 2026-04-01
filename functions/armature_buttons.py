import bpy
from test321 import glob_vars, i18n


######### Armature Buttons ###########
class BUTTON_BN(bpy.types.Operator):
    bl_label = i18n.t('button_bn')
    bl_idname = "object.button_bn"
    bl_options = {'REGISTER', 'UNDO'}
    bn: bpy.props.StringProperty(name="Added")  # type: ignore

    def execute(self, context):
        scene = context.scene
        rbx_prefs = scene.rbx_prefs
        bn = self.bn
        global bn_selection
        global bn_error
        global msh_selection
        global msh_error
        bn_error = None
        msh_error = None

        bn_items = [
            'Character_bones_blocky',
            'Character_bones_r15_boy',
            'Character_bones_r15_girl',
            'Character_bones_r15_woman',
        ]

        # Append Armature
        bn_split = bn.rsplit('_')

        if bn_split[-1] == 'arma':
            for x in range(len(bn_items)):
                if rbx_prefs.rbx_arma_enum == 'OP' + str(x + 1):
                    rbx_arma_spwn = bn_items[x]

            bpy.ops.wm.append(directory=glob_vars.addon_path + glob_vars.rbx_blend_file + glob_vars.ap_object,
                              filename=rbx_arma_spwn)
            bn_sel = bpy.context.selected_objects[0].name
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = None
            bpy.data.objects[bn_sel].select_set(True)
            bpy.context.view_layer.objects.active = bpy.data.objects[bn_sel]
            print("Armature Appended")

        # Recalculate Normals
        if bn == 'normal':
            bn_mesh = 0
            sel = bpy.context.selected_objects
            if len(sel) < 1:
                print(i18n.t('nothing_selected'))
                msh_selection = i18n.t('nothing_selected')
            else:
                for x in sel:
                    if x.type != 'MESH':
                        print(x.type + " Selected. Pls Select Only Mesh")
                        msh_selection = "Pls Select Only Mesh"
                        bn_mesh = 0
                    else:
                        bn_mesh = 1
                        msh_selection = None
                if bn_mesh == 1:
                    if bpy.context.mode == 'OBJECT':
                        bpy.ops.object.editmode_toggle()
                        bpy.ops.mesh.select_all(action='SELECT')
                    elif bpy.context.mode == 'EDIT_MESH':
                        bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.normals_make_consistent(inside=False)
                    bpy.ops.object.editmode_toggle()
                    msh_error = 'done_nml'
                    print(i18n.t('normals_recalculated'))

        # Remove Duplicated Vertices
        if bn == 'doubles':
            bn_mesh = 0
            sel = bpy.context.selected_objects
            if len(sel) < 1:
                print(i18n.t('nothing_selected'))
                msh_selection = i18n.t('nothing_selected')
            else:
                for x in sel:
                    if x.type != 'MESH':
                        print(x.type + " Selected. Pls Select Only Mesh")
                        msh_selection = "Pls Select Only Mesh"
                        bn_mesh = 0
                    else:
                        bn_mesh = 1
                        msh_selection = None
                if bn_mesh == 1:
                    if bpy.context.mode == 'OBJECT':
                        bpy.ops.object.editmode_toggle()
                        bpy.ops.mesh.select_all(action='SELECT')
                    elif bpy.context.mode == 'EDIT_MESH':
                        bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.remove_doubles()
                    bpy.ops.mesh.normals_make_consistent(inside=False)
                    bpy.ops.object.editmode_toggle()

                    bpy.ops.mesh.customdata_custom_splitnormals_clear()
                    if glob_vars.is_blender_version_below(4, 1):
                        bpy.context.object.data.use_auto_smooth = False
                    else:
                        bpy.ops.object.shade_auto_smooth()

                    msh_error = 'done_vts'
                    print(i18n.t('doubles_removed'))

        # Parent Armature
        if bn == 'parent':
            bn_arma = 0
            bn_mesh = 0

            sel = bpy.context.selected_objects
            if len(sel) < 1:
                print(i18n.t('nothing_selected'))
                bn_selection = i18n.t('nothing_selected')
            else:
                print(sel)
                if len(sel) > 2:
                    print(i18n.t('more_than_2_objects_selected'))
                    bn_selection = i18n.t('more_than_2_objects_selected')
                else:
                    if len(sel) < 2:
                        print(i18n.t('2_objects_must_be_selected'))
                        bn_selection = i18n.t('select_2_objects')
                    else:
                        for x in sel:
                            if x.type == 'ARMATURE':
                                bn_arma = 1
                                break
                        if bn_arma == 0:
                            print("No Bones Selected")
                            print(i18n.t('no_bones_selected'))
                            bn_selection = i18n.t('no_bones_selected')
                        for x in sel:
                            if x.type == 'MESH':
                                bn_mesh = 1
                                break
                        if bn_mesh == 0:
                            print("No Mesh Selected")
                            print(i18n.t('no_mesh_selected'))
                            bn_selection = i18n.t('no_mesh_selected')

            if bn_arma == 1 and bn_mesh == 1:
                bn_selection = None
                bn_active = bpy.context.view_layer.objects.active
                if bn_active.type != 'ARMATURE':
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = None
                    for x in sel:
                        if x.type == 'ARMATURE':
                            bpy.data.objects[x.name].select_set(True)
                            bpy.context.view_layer.objects.active = bpy.data.objects[x.name]
                        else:
                            bpy.data.objects[x.name].select_set(True)
                try:
                    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
                except:
                    bn_error = 1
                else:
                    print("Bones Successfully Parented")
                    print(i18n.t('bones_successfully_parented'))
                    bn_error = 2

        return {'FINISHED'}