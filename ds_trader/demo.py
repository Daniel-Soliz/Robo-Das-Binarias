"""Dados SINTÉTICOS determinísticos para aprender/testar, nunca rentabilidade."""
import csv
import io
from datetime import datetime, timedelta, timezone

def demo_csv():
    out=io.StringIO()
    w=csv.writer(out)
    w.writerow(['timestamp','asset','source','market','interval_seconds','open','high','low','close','volume','open_time','payout','payout_known_at'])
    # Dois topos iguais, rompimento, reteste e barras suficientes para liquidação.
    shape=[(1,1.0003,.9997,1.0001),(1.0001,1.0006,.9999,1.0003),
           (1.0003,1.001,.9999,1.0002),(1.0002,1.0005,.9998,1),
           (1,1.0004,.9996,1.0001),(1.0001,1.0006,.9998,1.0002),
           (1.0002,1.001,.9999,1.0003),(1.0003,1.0006,.9998,1.0001),
           (1.0001,1.0005,.9997,1.0002),(1.0002,1.0016,1.0001,1.0015),
           (1.0012,1.0018,1.001,1.0016),(1.0017,1.0019,1.0014,1.0018),
           (1.0018,1.002,1.0016,1.0019),(1.0019,1.0021,1.0017,1.002),
           (1.002,1.0023,1.0018,1.0021),(1.0021,1.0024,1.0019,1.0022),
           (1.0022,1.0025,1.002,1.0023),(1.0023,1.0026,1.0021,1.0024),
           (1.0024,1.0027,1.0022,1.0025),(1.0025,1.0028,1.0023,1.0026)]
    start=datetime(2025,1,6,12,tzinfo=timezone.utc)
    for cycle in range(10):
        for j,values in enumerate(shape):
            t=start+timedelta(minutes=cycle*len(shape)+j)
            # Alternância simétrica alta/baixa, preços artificiais.
            o,h,l,c=values
            if cycle%2:
                o,h,l,c=2-o,2-l,2-h,2-c
            stamp=t.isoformat()
            w.writerow([stamp,'DEMO-EURUSD','SINTETICO-DS-TESTE','REGULAR',60,o,h,l,c,'',stamp,0.8 if cycle%2 else 0.75,stamp])
    return out.getvalue()
