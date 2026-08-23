import numpy as np
from mathutils import Euler
from typing import List
from . import calc_utils, cgt_math, cgt_leveling, cgt_smoothing
from ..cgt_patterns import cgt_nodes


class PoseRotationCalculator(cgt_nodes.CalculatorNode, calc_utils.ProcessorUtils):
    shoulder_center = None
    hip_center = None
    rotation_data = []
    scale_data = []

    def __init__(self):
        self.shoulder_center = calc_utils.CustomData(34)
        self.pose_offset = calc_utils.CustomData(35)
        self.hip_center = calc_utils.CustomData(33)
        self.smoother = cgt_smoothing.LandmarkSmoother()

    def update(self, data: List, frame: int=-1):
        if not data or len(data) < 33:
            return [[], [], []], frame
        self.data = data
        for i in range(2):
            self.data.append([33 + i, [0., 0., 0.]])
        self.rotation_data = []
        self.scale_data = []
        self.prepare_landmarks()
        self.shoulder_hip_location()
        self.set_hip_as_origin()
        try:
            self.calculate_rotations()
        except AttributeError:
            pass
        if self.has_duplicated_results(self.data, "pose"):
            return [[], [], []], frame
        return [self.data, self.rotation_data, []], frame

    def calculate_rotations(self):
        self.shoulder_rotation()
        self.torso_rotation()
        self.limb_rotations()
        self.foot_rotation()

    def limb_rotations(self):
        def calc_chain_rotations(data):
            rotations = []
            for i in range(1, len(data)):
                quart = cgt_math.rotate_towards(data[i][1], data[i - 1][1], '-Y', 'Z')
                euler = self.try_get_euler(quart, prev_rot_idx=data[i - 1][0])
                rotations.append([data[i - 1][0], euler])
            return rotations
        left_leg = [self.data[23], self.data[25], self.data[27]]
        right_leg = [self.data[24], self.data[26], self.data[28]]
        left_arm = [self.data[11], self.data[13], self.data[15], self.data[19]]
        right_arm = [self.data[12], self.data[14], self.data[16], self.data[20]]
        for objs in [left_leg, right_leg, right_arm, left_arm]:
            self.rotation_data += calc_chain_rotations(objs)

    def foot_rotation(self):
        def rot_from_matrix(loc: List[np.array], tar_idx: int):
            tangent = cgt_math.normal_from_plane(loc)
            binormal = loc[0] - loc[2]
            normal = loc[1] - loc[2]
            vectors = [tangent, normal, binormal]
            matrix = cgt_math.generate_matrix(*[cgt_math.normalize(vec) for vec in vectors])
            _, quart, _ = cgt_math.decompose_matrix(matrix)
            return self.try_get_euler(quart, None, tar_idx)
        left_locations = [self.data[25][1], self.data[27][1], self.data[31][1]]
        left_foot_rot = rot_from_matrix(left_locations, self.data[27][0])
        self.rotation_data.append([self.data[27][0], left_foot_rot])
        right_locations = [self.data[26][1], self.data[28][1], self.data[32][1]]
        right_foot_rot = rot_from_matrix(right_locations, self.data[28][0])
        self.rotation_data.append([self.data[28][0], right_foot_rot])

    def torso_rotation(self):
        hip_center = cgt_math.center_point(np.array(self.data[23][1]), np.array(self.data[24][1]))
        right_hip = np.array(self.data[24][1])
        shoulder_center = cgt_math.center_point(np.array(self.data[11][1]), np.array(self.data[12][1]))
        vertices = np.array([self.data[23][1], self.data[24][1], shoulder_center])
        connections = np.array([[0, 1, 2]])
        normal = cgt_math.normal_from_plane([self.data[23][1], self.data[24][1], shoulder_center])
        tangent = cgt_math.normalize(cgt_math.to_vector(hip_center, right_hip))
        normal = cgt_math.normalize(normal)
        binormal = cgt_math.normalize(cgt_math.to_vector(hip_center, shoulder_center))
        matrix = cgt_math.generate_matrix(tangent, binormal, normal)
        loc, quart, scale = cgt_math.decompose_matrix(matrix)
        offset = [-.5, 0, 0]
        euler = self.try_get_euler(quart, offset, self.hip_center.idx)
        self.rotation_data.append([self.hip_center.idx, euler])

    def shoulder_rotation(self):
        shoulder_center = cgt_math.center_point(self.data[11][1], self.data[12][1])
        shoulder_rotation = cgt_math.rotate_towards(shoulder_center, self.data[12][1], 'Z')
        hip_center = cgt_math.center_point(self.data[23][1], self.data[24][1])
        hip_rotation = cgt_math.rotate_towards(hip_center, self.data[24][1], 'Z')
        offset = [0, 0, 0]
        shoulder_rot = self.try_get_euler(shoulder_rotation, offset, 7)
        hip_rot = self.try_get_euler(hip_rotation, offset, 8)
        euler = Euler((shoulder_rot[0] - hip_rot[0], shoulder_rot[1] - hip_rot[1], shoulder_rot[2] - hip_rot[2]))
        self.rotation_data.append([self.shoulder_center.idx, euler])

    def shoulder_hip_location(self):
        self.shoulder_center.loc = cgt_math.center_point(self.data[11][1], self.data[12][1])
        self.data.append([self.shoulder_center.idx, self.shoulder_center.loc])
        self.hip_center.loc = cgt_math.center_point(self.data[23][1], self.data[24][1])
        self.data.append([self.hip_center.idx, self.hip_center.loc])

    def prepare_landmarks(self):
        """Prepare landmarks, apply camera leveling, then smooth the pose."""
        self.data = [[idx, np.array([-landmark[0], landmark[2], -landmark[1]])] for idx, landmark in self.data]
        if cgt_leveling.LEVELING.enabled and cgt_leveling.LEVELING.mode != 'off':
            lookup = {idx: landmark for idx, landmark in self.data}
            if all(i in lookup for i in (11, 12, 23, 24)):
                shoulder_c = (lookup[11] + lookup[12]) / 2.0
                hip_c = (lookup[23] + lookup[24]) / 2.0
                up_vector = shoulder_c - hip_c
                if cgt_leveling.LEVELING.mode == 'ema':
                    cgt_leveling.LEVELING.feed_ema(up_vector)
            self.data = cgt_leveling.LEVELING.apply(self.data)
        self.data = self.smoother.smooth(self.data)

    def set_hip_as_origin(self):
        self.pose_offset.loc = self.hip_center.loc
        self.data = [[idx, np.array([landmark[0] - self.hip_center.loc[0],
                                     landmark[1] - self.hip_center.loc[1],
                                     landmark[2] - self.hip_center.loc[2]])]
                     for idx, landmark in self.data]
        self.data.append([self.pose_offset.idx, self.pose_offset.loc])
