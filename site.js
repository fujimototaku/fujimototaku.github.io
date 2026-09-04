(() => {
  const counter = document.querySelector("#counter-number");
  if (!counter) return;

  const baseDate = new Date("2026-09-04T00:00:00+09:00");
  const days = Math.max(0, Math.floor((Date.now() - baseDate.getTime()) / 86400000));
  const pretendVisitors = 42 + (days * 3);
  counter.textContent = String(pretendVisitors).padStart(8, "0");
})();
