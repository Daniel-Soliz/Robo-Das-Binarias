"""Explicações determinísticas, sem IA externa e sem envio de dados."""
def explain(event):
    return (f"{event['asset']} • {event['source']} • {event['market']}\n"
            f"{event['time']} (UTC) — {event['status']} / {event['direction']}\n"
            f"Região: {event['lower']:.8g} a {event['upper']:.8g}; toques: {event['touches']}.\n"
            f"{event['reason']}\n"
            'Hipótese experimental. Critérios atendidos não são probabilidade de acerto.')
