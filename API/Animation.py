from .AnimationIOWrappers import AnimFrameData
import bpy
from .. import CommonUtils

# Rest-pose tolerances for dropping a channel: 0.25 mm, 1e-6 on the quaternion's real part (0.08 degrees), 0.1 percent scale.
TRANSLATION_EPS = 0.00025
ROTATION_EPS = 0.000001
SCALE_EPS = 0.001

class AnimData():
    def __init__(self):
        self.frames = {}
        self.name = "UNKNOWN ANIMATION"
        self.start = 0
        self.end = 1

    def SetAnimationAttributes(self, armature_obj):
        armature_obj.sf_anim_props.anim_name = self.name

    def LoadAnimationAttributes(self, armature_obj):
        self.name = armature_obj.sf_anim_props.anim_name

    def GetFrameCount(self):
        return len(list(self.frames.keys()))

    def GetFrame(self, frame_number):
        str_frame_number = str(frame_number)
        if str_frame_number not in self.frames:
            return None
        return self.frames[str_frame_number]

    def AddGetFrame(self, frame_number):
        frame = self.GetFrame(frame_number)

        str_frame_number = str(frame_number)
        if frame == None:
            self.frames.update({str_frame_number: AnimFrameData()})

        return self.frames[str_frame_number]

    def GetBoneList(self):
        bones = []
        for frame in self.frames:
            for bdata in frame.bone_data:
                bones.append(bdata.bone_name)
        return bones

    def LoadFromBlender(self, armature, rig_name_id_mapping):
        if CommonUtils.GetBlenderVersion()[0] == 5:
            from bpy_extras import anim_utils

        self.LoadAnimationAttributes(armature)
        self.frames.clear()
        num_anim_frames = 0

        action = armature.animation_data.action

        if CommonUtils.GetBlenderVersion()[0] == 5:
            slot = action.slots[0] # for now
            channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)

            for fcurve in channelbag.fcurves:
                for kp in fcurve.keyframe_points:
                    frame_num = int(kp.co[0])
                    num_anim_frames = max(frame_num, num_anim_frames)
        else:
            for fcurve in action.fcurves:
                for kp in fcurve.keyframe_points:
                    frame_num = int(kp.co[0])
                    num_anim_frames = max(frame_num, num_anim_frames)

        num_anim_frames += 1
        # Per bone, whether each channel ever leaves the rest pose.
        animated = {}

        for frame_num in range(0, num_anim_frames, 1):

            frame = self.AddGetFrame(frame_num)
            bpy.context.scene.frame_set(frame_num)

            depsgraph = bpy.context.evaluated_depsgraph_get()
            depsgraph.update()
            armature = armature.evaluated_get(depsgraph)

            for pose_bone in armature.pose.bones:

                bone_name = pose_bone.name

                M = armature.convert_space(
                    pose_bone=pose_bone,
                    matrix=pose_bone.matrix,
                    from_space='POSE',
                    to_space='LOCAL',
                ).decompose()

                translation = M[0]
                rotation = M[1]
                scale = M[2]

                bone = frame.bone_data[frame.AddGetBoneIndexBoneName(bone_name)]
                bone.translation.blender = translation
                bone.rotation.blender_quaternion = rotation
                bone.scale.blender = scale

                flags = animated.setdefault(bone_name, [False, False, False])
                flags[0] = flags[0] or translation.length > TRANSLATION_EPS
                flags[1] = flags[1] or 1.0 - abs(rotation.w) > ROTATION_EPS
                flags[2] = flags[2] or max(abs(s - 1.0) for s in scale) > SCALE_EPS

                #id
                bone.index = rig_name_id_mapping[bone.bone_name]

        # A channel that stays at rest on every frame is left out of the file, as in the game's own clips, so the rig and runtime systems keep that bone.
        for frame in self.frames.values():
            for bone in frame.bone_data:
                moved, rotated, scaled = animated.get(bone.bone_name, (True, True, True))
                if not moved:
                    bone.translation.raw = (None, None, None)
                if not rotated:
                    bone.rotation.raw_xyzw = (None, None, None, None)
                if not scaled:
                    bone.scale.raw = None
