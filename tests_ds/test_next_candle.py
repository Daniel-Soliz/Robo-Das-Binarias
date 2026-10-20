"""Regras de proxima vela: abstencao, padroes, LTA/LTB, sem futuro ou estatisticas falsas."""
import unittest
from dataclasses import dataclass
from ds_trader.next_candle import evaluate_next, _pivots, _line, _patterns


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float


def sequence(n=35):
    bars=[]
    for i in range(n):
        base=1.1+.0006*i
        step=(i%5-2)*.0007
        op=base+step
        cl=op+(.0003 if i%2 else -.0002)
        bars.append(Bar(op,max(op,cl)+.0004,min(op,cl)-.0004,cl))
    return bars


class StructuralRules(unittest.TestCase):
    def test_requires_closed_confirmed_and_minimum_history(self):
        bars=sequence()
        result=evaluate_next(bars,source="screen",closed_confirmed=False)
        self.assertEqual(result.side,"AGUARDAR")
        self.assertIn("Fechamento",result.reasons[0])
        self.assertEqual(evaluate_next(bars[:15],source="api",closed_confirmed=True).side,"AGUARDAR")
        self.assertIn("Cotacoes do fornecedor",evaluate_next(bars,source="api",closed_confirmed=True).caveat)

    def test_only_five_bar_confirmed_pivots(self):
        b=[Bar(1,2,1,1.5),Bar(1,2.2,1,1.5),Bar(1,3,1,1.5),
           Bar(1,2,1,1.5),Bar(1,2,1,1.5)]
        self.assertEqual(_pivots(b,"high"),[(2,3)])
        self.assertEqual(_pivots(b[:4],"high"),[])

    def test_lta_and_ltb_require_structural_ascending_descending(self):
        self.assertEqual(_line([(2,1.0),(8,1.1)],10,True),(1.1+(1.1-1.0)/6,1.1+2*(1.1-1.0)/6))
        self.assertIsNotNone(_line([(2,1.3),(9,1.1)],11,False))
        self.assertIsNone(_line([(2,1.3),(9,1.1)],11,True))
        self.assertIsNone(_line([(2,1.0),(8,1.1)],30,True))

    def test_engulf_patterns_and_doji(self):
        b=Bar(1.100,1.101,1.097,1.098)
        up=Bar(1.0975,1.103,1.097,1.102)
        self.assertIn("Engolfo de alta",_patterns([b,up]))
        down=Bar(1.103,1.104,1.096,1.097)
        self.assertIn("Engolfo de baixa",_patterns([up,down]))
        doji=Bar(1.1000,1.1010,1.0990,1.10001)
        self.assertIn("Doji / indecisao",_patterns([b,doji]))

    def test_doji_forces_wait_even_if_prior_trending(self):
        b=sequence()
        old=b[-1]
        b[-1]=Bar(old.open,old.open+.005,old.open-.005,old.open)
        result=evaluate_next(b,source="api",closed_confirmed=True)
        self.assertEqual(result.side,"AGUARDAR")
        self.assertIn("Doji / indecisao",result.patterns)

    def test_constant_ohlc_never_generates_signal(self):
        b=[Bar(1,1,1,1)]*40
        result=evaluate_next(b,source="api",closed_confirmed=True)
        self.assertEqual(result.side,"AGUARDAR")

    def test_opinion_has_reasons_and_no_fictional_probability(self):
        result=evaluate_next(sequence(),source="screen",closed_confirmed=True)
        self.assertIn(result.side,("CALL","PUT","AGUARDAR"))
        self.assertTrue(result.reasons)
        self.assertTrue(result.caveat)
        self.assertFalse(hasattr(result,"win_probability"))
        self.assertFalse(hasattr(result,"expiry_time"))
        self.assertIn("Pixels",result.caveat)


if __name__=="__main__":
    unittest.main()
