import type { ReactNode } from "react";

import { NurseStation } from "./NurseStation";
import { SceneDefs } from "./SceneDefs";

/** 可延伸的剖面病房：牆、地板與走道以程式排版，床數不寫入素材。 */
export function WardRoom({ children }: { children: ReactNode }) {
  return (
    <section className="ward-room relative">
      <SceneDefs />
      <div
        aria-hidden="true"
        className="room-rear-wall absolute inset-x-0 top-0 h-20"
      >
        <div className="absolute inset-x-12 top-8 h-1 rounded-full bg-scene-lamp shadow-lamp" />
        <div className="absolute top-2 right-10 flex gap-10">
          {[0, 1, 2].map((window) => (
            <div
              key={window}
              className="h-8 w-24 rounded-sm window-blinds ring-4 ring-scene-wall-cap"
            />
          ))}
        </div>
      </div>
      <div aria-hidden="true" className="room-side-wall room-side-left" />
      <div aria-hidden="true" className="room-side-wall room-side-right" />
      <div className="relative px-5 pt-16 sm:px-7">{children}</div>
      <div className="relative flex justify-center pt-8 pb-12">
        <NurseStation className="w-80 max-w-[55%] drop-shadow-xl" />
      </div>
    </section>
  );
}
