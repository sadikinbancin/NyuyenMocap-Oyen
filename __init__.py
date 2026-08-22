'''
Copyright (C) Denys Hsu, cgtinker, cgtinker.com, hello@cgtinker.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

bl_info = {
    "name": "BlendArMocap NX",
    "description": (
        "Modern MediaPipe Tasks port of BlendArMocap with offline pose, hand and face "
        "tracking, optional viewport skeleton preview, and Rigify transfer helpers."
    ),
    "author": "cgtinker (original) — Ivan / Claude (Tasks API port)",
    "version": (1, 8, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Tool",
    "doc_url": "https://cgtinker.github.io/BlendArMocap/",
    "tracker_url": "https://github.com/sadikinbancin/NyuyenMocap-Oyen/issues",
    "support": "COMMUNITY",
    "category": "Animation",
}


def register():
    from .src import cgt_registration
    cgt_registration.register()
    from .src import nyuyen_runtime
    nyuyen_runtime.register_runtime_features()


def unregister():
    try:
        from .src import nyuyen_runtime
        nyuyen_runtime.unregister_runtime_features()
    finally:
        from .src import cgt_registration
        cgt_registration.unregister()


if __name__ == '__main__':
    register()
