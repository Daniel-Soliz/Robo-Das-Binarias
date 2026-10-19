"""DS Trader desktop; diagnóstico anterior preservado em legacy_main.py."""
if __name__ == '__main__':
    import sys
    if '--smoke-test' in sys.argv:
        import json
        from pathlib import Path
        from scripts.gui_smoke import run
        try:
            result=run()
            Path('smoke-result.json').write_text(json.dumps(result),encoding='utf-8')
        except Exception:
            import traceback
            Path('smoke-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            raise
    else:
        from ds_trader.ui import main
        main()
