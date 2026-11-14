"""Exercise the deployed timeout without leaving an intercepted request pending."""

def stalled_feed_deadline(page):
    pattern = "**/__audit_stalled_feed__*"
    pending = []
    def handler(route):
        pending.append(route)
    page.route(pattern, handler)
    try:
        return page.evaluate("""async () => {
          const started=performance.now();
          try {
            await fetchData(new URL('__audit_stalled_feed__',location.href).href,'json',120);
            return {rejected:false,elapsed_ms:performance.now()-started};
          } catch(error) {
            return {rejected:true,error:String(error.message),elapsed_ms:performance.now()-started};
          }
        }""")
    finally:
        # AbortController settles the browser fetch, but the Playwright route
        # still needs a terminal action before its browser context is closed.
        for route in pending:
            route.abort("aborted")
        page.unroute(pattern, handler)
