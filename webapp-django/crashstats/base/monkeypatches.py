

def patch():
    import jingo.monkey
    jingo.monkey.patch()

    import session_csrf
    session_csrf.monkeypatch()

    import jingo
    from compressor.contrib.jinja2ext import CompressorExtension
    jingo.env.add_extension(CompressorExtension)
