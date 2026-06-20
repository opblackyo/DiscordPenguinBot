const modules = [
  ["Discord bot", "Phase 0 skeleton ready"],
  ["FastAPI", "Health endpoint ready"],
  ["Lavalink", "Private v4 node configured"],
  ["Music", "Planned for Phase 1"],
  ["AI adapter", "Planned for Phase 4"],
];

export default function App() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">DISCORD PENGUIN BOT</p>
        <h1>Control center skeleton</h1>
        <p>
          Phase 0 establishes service boundaries. Live status, authentication,
          and media controls arrive in later phases.
        </p>
      </section>
      <section className="module-grid" aria-label="Planned modules">
        {modules.map(([name, state]) => (
          <article key={name}>
            <h2>{name}</h2>
            <p>{state}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
