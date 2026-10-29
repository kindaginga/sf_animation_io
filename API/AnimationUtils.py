import math
import mathutils

bone_axis_correction = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'Z')
bone_axis_correction_inv = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'Z')

bone_axis_correction_full = mathutils.Matrix.Rotation(math.radians(180.0), 4, 'Z')
bone_axis_correction_full_inv = mathutils.Matrix.Rotation(math.radians(-180.0), 4, 'Z')

def BoneAxisCorrection(T):
    return bone_axis_correction @ T @ bone_axis_correction_inv

def BoneAxisCorrectionInv(T):
    return bone_axis_correction_inv @ T @ bone_axis_correction

def BoneAxisCorrection_Alt(T):
    return (bone_axis_correction_full @ T @ bone_axis_correction_inv)

def LoadAnim(armature_obj, frame_num, frame_bones_list):
    pose_bones = armature_obj.pose.bones

    for frame_bone in frame_bones_list:
        if pose_bones.get(frame_bone.bone_name) == None:
            raise Exception((f"No pose-bone found", frame_bone.bone_name))
        else:
            pose_bone = pose_bones.get(frame_bone.bone_name)

        SetAnimationBoneMatrix(frame_bone, pose_bone, frame_num)

def QuaternionFcurves(armature_obj):
    # Returns {bone data path: {channel index: fcurve}} for every rotation_quaternion curve of the armature's action.
    action = armature_obj.animation_data.action
    if hasattr(action, "layers") and len(action.layers):
        fcurves = [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    else:
        fcurves = list(action.fcurves)
    groups = {}
    for fc in fcurves:
        if fc.data_path.endswith(".rotation_quaternion"):
            groups.setdefault(fc.data_path, {})[fc.array_index] = fc
    return groups

def MakeQuaternionKeysContinuous(armature_obj):
    # Negates each rotation key whose quaternion lies in the opposite hemisphere from the bone's previous key, so a per-channel interpolation between keys never passes through a wrong rotation; returns the number of keys negated.
    if armature_obj.animation_data is None or armature_obj.animation_data.action is None:
        return 0
    negated = 0
    for channels in QuaternionFcurves(armature_obj).values():
        if len(channels) != 4:
            continue
        keys = [{round(kp.co[0], 4): kp for kp in channels[i].keyframe_points} for i in range(4)]
        frames = sorted(set(keys[0]).intersection(*keys[1:]))
        prev = None
        for f in frames:
            q = [keys[i][f].co[1] for i in range(4)]
            if prev is not None and sum(a * b for a, b in zip(q, prev)) < 0.0:
                for i in range(4):
                    kp = keys[i][f]
                    kp.co[1] = -kp.co[1]
                    kp.handle_left[1] = -kp.handle_left[1]
                    kp.handle_right[1] = -kp.handle_right[1]
                q = [-x for x in q]
                negated += 1
            prev = q
    for channels in QuaternionFcurves(armature_obj).values():
        for fc in channels.values():
            fc.update()
    return negated

def SetAnimationBoneMatrix(frame_bone, pose_bone, frame_num):
    pose_bone.rotation_mode = 'QUATERNION'

    if not frame_bone.scale.is_none:
        pose_bone.scale = frame_bone.scale.blender
        pose_bone.keyframe_insert(data_path='scale', frame=frame_num)
    if not frame_bone.translation.is_none:
        pose_bone.location = frame_bone.translation.blender
        pose_bone.keyframe_insert(data_path='location', frame=frame_num)
    if not frame_bone.rotation.is_none:
        pose_bone.rotation_quaternion = frame_bone.rotation.blender_quaternion
        pose_bone.keyframe_insert(data_path='rotation_quaternion', frame=frame_num)
        temp = frame_bone.rotation.blender_quaternion.to_euler()
        print(math.degrees(temp.x), math.degrees(temp.y), math.degrees(temp.z))
