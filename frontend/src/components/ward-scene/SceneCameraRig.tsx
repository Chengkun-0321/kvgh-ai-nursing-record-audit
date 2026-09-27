"use client";

import { useThree } from "@react-three/fiber";
import { useLayoutEffect } from "react";
import type { Camera } from "three";

import type { CameraChannel, MapCamera } from "@/lib/wardMap";
import {
  type CameraPose,
  getSceneCameraPose,
  type MapFrame,
  VIEW_ROTATION,
} from "@/lib/wardProjection";

type SceneCameraRigProps = {
  channel: CameraChannel;
  frame: MapFrame;
};

function applyPose(camera: Camera, pose: CameraPose) {
  camera.rotation.set(
    VIEW_ROTATION.x,
    VIEW_ROTATION.y,
    VIEW_ROTATION.z,
    VIEW_ROTATION.order,
  );
  camera.position.set(...pose.position);
  if ("zoom" in camera && "updateProjectionMatrix" in camera) {
    camera.zoom = pose.zoom;
    (camera.updateProjectionMatrix as () => void)();
  }
}

/**
 * 地圖控制器每次重繪時同步設定 3D 相機，並立即算出這一幀（advance），
 * 讓 DOM 病床按鈕與 3D 畫面在同一幀移動，平移時不會錯位。
 */
export function SceneCameraRig({ channel, frame }: SceneCameraRigProps) {
  const get = useThree((state) => state.get);
  const size = useThree((state) => state.size);

  useLayoutEffect(() => {
    const render = (mapCamera: MapCamera) => {
      const state = get();
      applyPose(state.camera, getSceneCameraPose(mapCamera, state.size, frame));
      state.advance(performance.now());
    };
    render(channel.getCurrent());
    return channel.subscribe(render);
  }, [channel, frame, get, size]);

  return null;
}
