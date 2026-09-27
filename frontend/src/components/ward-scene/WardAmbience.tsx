/** 病房延伸到導覽背後的失焦環境，建立玻璃介面與實體空間的深度。 */
export function WardAmbience() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden scene-ambient"
    >
      <div className="ambient-corridor absolute -inset-20 blur-xl" />
      <div className="absolute inset-0 bg-linear-to-b from-scene-ambient/60 via-transparent to-scene-ambient/25" />
    </div>
  );
}
