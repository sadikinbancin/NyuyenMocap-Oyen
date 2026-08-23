import numpy as np
from . import calc_utils, cgt_math, cgt_leveling
from ..cgt_patterns import cgt_nodes


class HandRotationCalculator(cgt_nodes.CalculatorNode, calc_utils.ProcessorUtils):
    fingers = [[1, 5], [5, 9], [9, 13], [13, 17], [17, 21]]
    data: np.ndarray = None
    left_hand_data: np.ndarray = None
    right_hand_data: np.ndarray = None
    left_angles: list = None
    right_angles: list = None
    left_scale: np.ndarray = None
    right_scale: np.ndarray = None

    def init_data(self):
        self.left_hand_data = self.set_global_origin(self.data[0])
        self.right_hand_data = self.set_global_origin(self.data[1])
        self.left_angles = self.finger_angles(self.left_hand_data)
        self.right_angles = self.finger_angles(self.right_hand_data)
        left_hand_rot = self.global_hand_rotation(self.left_hand_data, 0, "L")
        if left_hand_rot is not None:
            self.left_angles.append(left_hand_rot)
        right_hand_rot = self.global_hand_rotation(self.right_hand_data, 100, "R")
        if right_hand_rot is not None:
            self.right_angles.append(right_hand_rot)

    def update(self, data, frame=-1):
        locations = [[], []]
        angles = [[], []]
        self.data = data
        self.init_data()
        if self.right_hand_data is not None and not self.has_duplicated_results(self.right_hand_data, "hand", 0):
            locations[1] = self.right_hand_data
            angles[1] = self.right_angles
        if self.left_hand_data is not None and not self.has_duplicated_results(self.left_hand_data, "hand", 1):
            locations[0] = self.left_hand_data
            angles[0] = self.left_angles
        return [locations, angles, [[], []]], frame

    def finger_angles(self, hand):
        if not hand or len(hand) < 20:
            return []
        x_angles = self.get_x_angles(hand)
        z_angles = self.get_z_angles(hand)
        data = []
        for idx in range(0, 20):
            if x_angles[idx] != 0 or z_angles[idx] != 0:
                data.append([idx, np.array([x_angles[idx], 0, z_angles[idx]])])
        return data

    def get_z_angles(self, hand):
        data = [0] * 20
        joints = np.array([[0, 1, 2]])

        def calculate_thumb_angle():
            plane = np.array([np.array([0, 0, 0]), hand[1][1], hand[5][1]])
            thumb_proj = [cgt_math.project_vec_on_plane(plane, joints, p)
                          for p in [hand[1][1], hand[5][1], hand[2][1]]]
            thumb_vecs = [cgt_math.to_vector(tp[0], tp[1]) for tp in [
                [thumb_proj[0], thumb_proj[1]], [thumb_proj[0], thumb_proj[2]]]]
            return cgt_math.angle_between(np.array(thumb_vecs[0]), np.array(thumb_vecs[1]))

        data[1] = calculate_thumb_angle()
        tangent = cgt_math.to_vector(np.array(hand[5][1]), np.array(hand[17][1]))
        mcps = [cgt_math.project_point_on_vector(np.array(hand[finger[0]][1]), np.array(hand[5][1]), np.array(hand[17][1]))
                for finger in self.fingers[1:]]
        pips = [np.array(hand[finger[1] - 2][1]) for finger in self.fingers[1:]]
        dists = [cgt_math.get_vector_distance(mcps[i], pips[i]) for i in range(0, 4)]
        pinky_vec = cgt_math.to_vector(np.array(hand[0][1]), np.array(hand[17][1]))
        thumb_vec = cgt_math.to_vector(np.array(hand[1][1]), np.array(hand[5][1]))
        dirs = [pinky_vec, pinky_vec, thumb_vec, thumb_vec]
        points = 20
        for i in range(0, 4):
            circle = cgt_math.create_circle_around_vector(tangent, mcps[i], dists[i], points, dirs[i])
            closest = cgt_math.get_closest_idx(pips[i], circle)
            mcp_pip = cgt_math.to_vector(mcps[i], pips[i])
            mcp_closest = cgt_math.to_vector(mcps[i], circle[closest])
            expanded_circle = circle + circle + circle
            a = expanded_circle[closest + points + 6]
            b = expanded_circle[closest + points - 6]
            plane = np.array([a, circle[closest], b])
            normal = cgt_math.normalize(cgt_math.normal_from_plane(plane))
            dist = cgt_math.distance_from_plane(pips[i], normal, circle[closest])
            angle = cgt_math.angle_between(np.array(mcp_pip), np.array(mcp_closest))
            if dist < 0:
                angle = -angle
            data[self.fingers[i + 1][0]] = angle
        return data

    def get_x_angles(self, hand):
        fingers = [[hand[idx][1] for idx in range(finger[0], finger[1])] for finger in self.fingers]
        wrist_origin = np.array([0, 0, 0])
        fingers = [np.array([wrist_origin] + finger) for finger in fingers]
        joints = np.array([[0, 1, 2]])
        for idx, finger in enumerate(fingers):
            plane = np.array([np.array([0, 0, 0]), finger[1], finger[4]])
            fingers[idx] = [cgt_math.project_vec_on_plane(plane, joints, p) for p in finger]
        x_joints = [[0, 1, 2], [1, 2, 3], [2, 3, 4]]
        x_finger_angles = [cgt_math.joint_angles(finger, x_joints) for finger in fingers]
        data = [0] * 20
        for idx, angles in enumerate(x_finger_angles):
            if angles is None:
                break
            mcp, tip = self.fingers[idx]
            for angle_idx, finger_idx in enumerate(range(mcp, tip - 1)):
                data[finger_idx] = angles[angle_idx]
        return data

    def global_hand_rotation(self, hand, combat_idx_offset: int = 0, orientation: str = "R"):
        if hand == []:
            return []
        rotation = [-60, 60, 0] if orientation == "R" else [-60, -60, 0]
        rotated_points = [cgt_math.rotate_point_euler(np.array(hand[idx][1]), rotation) for idx in [1, 5, 13]]
        tangent = cgt_math.normalize(cgt_math.to_vector(rotated_points[0], rotated_points[1]))
        binormal = cgt_math.normalize(cgt_math.to_vector(rotated_points[1], rotated_points[2]))
        normal = cgt_math.normalize(np.cross(binormal, tangent))
        try:
            matrix = cgt_math.generate_matrix(normal, tangent, binormal)
            loc, quart, sca = cgt_math.decompose_matrix(matrix)
            euler = self.try_get_euler(quart, prev_rot_idx=combat_idx_offset)
            return [0, euler]
        except TypeError:
            return ()

    def landmarks_to_hands(self, left_hand, right_hand):
        return self.set_global_origin(left_hand), self.set_global_origin(right_hand)

    @staticmethod
    def set_global_origin(data):
        """Set wrist to origin after Blender-axis conversion and optional leveling."""
        if data is None or len(data) == 0:
            return data
        if len(data) > 0:
            data = [[idx, np.array([-landmark[0], landmark[2], -landmark[1]])] for idx, landmark in data[0]]
            data = cgt_leveling.LEVELING.apply(data)
            data = [[idx, landmark - data[0][1]] for idx, landmark in data]
        return data
