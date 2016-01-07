

def patch():
    import jingo.monkey
    jingo.monkey.patch()

    import session_csrf
    session_csrf.monkeypatch()
