# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

import sys
from pathlib import Path

# Add current dir to sys.path so twin_engine_pb2 can be imported by twin_engine_pb2_grpc
_proto_dir = str(Path(__file__).resolve().parent)
if _proto_dir not in sys.path:
    sys.path.insert(0, _proto_dir)

from . import twin_engine_pb2
from . import twin_engine_pb2_grpc

__all__ = ["twin_engine_pb2", "twin_engine_pb2_grpc"]
