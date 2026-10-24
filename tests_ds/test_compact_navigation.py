"""A navegação simples não pode eliminar recursos que já existiam."""
import unittest

from ds_trader.dashboard_shell import NAV_ITEMS, MORE_ITEMS


class CompactNavigationTests(unittest.TestCase):
    def test_three_main_destinations_and_five_secondary_destinations(self):
        self.assertEqual([key for key, _, _ in NAV_ITEMS],
                         ["live", "radar", "events"])
        self.assertEqual([key for key, _ in MORE_ITEMS],
                         ["overview", "forex", "chart", "reports", "config", "help"])
        self.assertEqual(len({key for key, *_ in NAV_ITEMS} |
                             {key for key, _ in MORE_ITEMS}), 9)


if __name__ == "__main__":
    unittest.main()
