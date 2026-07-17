export function ReplayControls({
  sequence,
  min,
  max,
  onChange,
}: {
  sequence: number;
  min: number;
  max: number;
  onChange: (sequence: number) => void;
}) {
  return (
    <label className="replay-controls">
      Replay event {sequence} / {max}
      <input
        aria-label="Replay event sequence"
        type="range"
        min={min}
        max={max}
        value={sequence}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
