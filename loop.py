import os
import json
import datetime
import subprocess
import anthropic

STATE_FILE = "state.json"
INDEX_FILE = "index.html"
MAX_ITEMS = 5

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "iteration": 0,
        "status": "RUNNING",
        "items": [],
        "history": []
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def call_agent(state):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    prompt = f"""Você é um agente que gerencia uma lista de tarefas concluídas.

Estado atual:
- Iteração: {state['iteration']}
- Itens concluídos até agora: {json.dumps(state['items'], ensure_ascii=False)}
- Total de itens: {len(state['items'])} de {MAX_ITEMS}

Sua tarefa: Decida qual nova tarefa técnica foi concluída nesta iteração. 
Escolha algo relacionado ao desenvolvimento de software (ex: "Escrevi testes unitários", "Refatorei o módulo de auth", "Otimizei queries do banco").
Seja criativo e específico. Não repita itens já existentes.

Responda APENAS com um JSON válido neste formato:
{{
  "decision": "o que você decidiu fazer nesta iteração",
  "new_item": "descrição curta da tarefa concluída (máximo 60 caracteres)",
  "reasoning": "por que esta tarefa foi priorizada (1 frase)"
}}"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)

def generate_html(state):
    status_color = "#00ff88" if state["status"] == "RUNNING" else "#ff6b35"
    status_label = "● RODANDO" if state["status"] == "RUNNING" else "✓ CONCLUÍDO"
    progress = len(state["items"])
    progress_pct = (progress / MAX_ITEMS) * 100

    history_rows = ""
    for i, entry in enumerate(reversed(state["history"])):
        row_class = "row-even" if i % 2 == 0 else "row-odd"
        history_rows += f"""
        <tr class="{row_class}">
          <td class="td-iter">#{entry['iteration']}</td>
          <td class="td-time">{entry['timestamp']}</td>
          <td class="td-item">{entry['item']}</td>
          <td class="td-reason">{entry['reasoning']}</td>
        </tr>"""

    items_html = ""
    for i in range(MAX_ITEMS):
        if i < len(state["items"]):
            items_html += f'<div class="task done"><span class="check">✓</span>{state["items"][i]}</div>'
        else:
            items_html += f'<div class="task pending"><span class="check">○</span>aguardando próxima iteração...</div>'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Loop Demo — Agent Dashboard</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg: #0a0a0f;
      --surface: #111118;
      --surface2: #1a1a24;
      --border: #2a2a38;
      --accent: #6c63ff;
      --accent2: #00ff88;
      --text: #e8e8f0;
      --muted: #666680;
      --mono: 'JetBrains Mono', monospace;
      --sans: 'Inter', sans-serif;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      min-height: 100vh;
      padding: 0;
    }}

    /* Header */
    .header {{
      border-bottom: 1px solid var(--border);
      padding: 20px 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .logo {{
      font-family: var(--mono);
      font-size: 13px;
      color: var(--muted);
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}

    .logo span {{
      color: var(--accent);
    }}

    .status-pill {{
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      color: {status_color};
      border: 1px solid {status_color}44;
      background: {status_color}11;
      padding: 6px 14px;
      border-radius: 100px;
    }}

    /* Main layout */
    .main {{
      max-width: 900px;
      margin: 0 auto;
      padding: 48px 40px;
    }}

    /* Hero */
    .hero {{
      margin-bottom: 48px;
    }}

    .iter-badge {{
      font-family: var(--mono);
      font-size: 11px;
      color: var(--muted);
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 12px;
    }}

    .hero-number {{
      font-family: var(--mono);
      font-size: clamp(64px, 12vw, 120px);
      font-weight: 700;
      line-height: 1;
      color: var(--text);
      letter-spacing: -0.03em;
      margin-bottom: 8px;
    }}

    .hero-number span {{
      color: var(--accent);
    }}

    .hero-sub {{
      font-size: 14px;
      color: var(--muted);
      font-weight: 300;
    }}

    /* Progress */
    .section-label {{
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 16px;
    }}

    .progress-section {{
      margin-bottom: 48px;
    }}

    .progress-bar-wrap {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 2px;
      height: 6px;
      margin-bottom: 24px;
      overflow: hidden;
    }}

    .progress-bar-fill {{
      height: 100%;
      width: {progress_pct}%;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      transition: width 0.4s ease;
      border-radius: 2px;
    }}

    .tasks {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .task {{
      font-size: 13px;
      padding: 12px 16px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      gap: 12px;
      border: 1px solid var(--border);
    }}

    .task.done {{
      background: var(--surface);
      color: var(--text);
    }}

    .task.pending {{
      background: transparent;
      color: var(--muted);
      border-style: dashed;
    }}

    .check {{
      font-family: var(--mono);
      font-size: 12px;
      color: var(--accent2);
      width: 16px;
      flex-shrink: 0;
    }}

    .task.pending .check {{
      color: var(--border);
    }}

    /* History table */
    .history-section {{
      margin-bottom: 48px;
    }}

    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 4px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-family: var(--mono);
      font-size: 12px;
    }}

    th {{
      text-align: left;
      padding: 10px 16px;
      font-size: 10px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      background: var(--surface);
      font-weight: 600;
    }}

    td {{
      padding: 12px 16px;
      vertical-align: top;
      color: var(--text);
    }}

    .row-even td {{ background: var(--surface); }}
    .row-odd td {{ background: var(--bg); }}

    .td-iter {{ color: var(--accent); width: 60px; }}
    .td-time {{ color: var(--muted); white-space: nowrap; width: 160px; }}
    .td-item {{ font-weight: 600; }}
    .td-reason {{ color: var(--muted); font-family: var(--sans); font-size: 12px; }}

    /* Footer */
    .footer {{
      border-top: 1px solid var(--border);
      padding: 20px 40px;
      font-family: var(--mono);
      font-size: 11px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
    }}

    @media (max-width: 600px) {{
      .header, .main, .footer {{ padding-left: 20px; padding-right: 20px; }}
      .hero-number {{ font-size: 72px; }}
      .td-reason {{ display: none; }}
    }}
  </style>
</head>
<body>

  <header class="header">
    <div class="logo"><span>/</span>loop-demo</div>
    <div class="status-pill">{status_label}</div>
  </header>

  <main class="main">

    <section class="hero">
      <div class="iter-badge">iteração atual</div>
      <div class="hero-number">{state['iteration']}<span>.</span></div>
      <div class="hero-sub">O agente tomou {state['iteration']} decisões até agora. Você não promitou nenhuma delas.</div>
    </section>

    <section class="progress-section">
      <div class="section-label">progresso — {progress} de {MAX_ITEMS} tarefas</div>
      <div class="progress-bar-wrap">
        <div class="progress-bar-fill"></div>
      </div>
      <div class="tasks">
        {items_html}
      </div>
    </section>

    <section class="history-section">
      <div class="section-label">histórico de decisões</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>iter</th>
              <th>timestamp</th>
              <th>tarefa concluída</th>
              <th>raciocínio</th>
            </tr>
          </thead>
          <tbody>
            {history_rows if history_rows else '<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:32px">Nenhuma iteração ainda. O loop rodará em breve.</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>

  </main>

  <footer class="footer">
    <span>github.com/loop-demo</span>
    <span>atualizado via github actions · cron 30min</span>
  </footer>

</body>
</html>"""
    return html

def main():
    state = load_state()
    
    if state["status"] == "COMPLETED":
        print("Loop já concluído. Nada a fazer.")
        return

    state["iteration"] += 1
    print(f"Iteração #{state['iteration']} iniciando...")

    result = call_agent(state)
    print(f"Agente decidiu: {result['new_item']}")

    state["items"].append(result["new_item"])
    state["history"].append({
        "iteration": state["iteration"],
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "item": result["new_item"],
        "reasoning": result["reasoning"],
        "decision": result["decision"]
    })

    if len(state["items"]) >= MAX_ITEMS:
        state["status"] = "COMPLETED"
        print("Stopping condition atingida. Loop concluído.")

    save_state(state)

    html = generate_html(state)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"index.html gerado. Status: {state['status']}")

if __name__ == "__main__":
    main()
