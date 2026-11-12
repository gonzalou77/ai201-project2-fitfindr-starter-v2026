# Live trials, Render deploy

Service: https://ai201-project2-fitfindr-starter-v2026-tewx.onrender.com
Query: `90s track jacket in size XS` (criterion 5 rescue)
Method: `curl -X POST /ask`, one request per trial, response saved as JSON here.
Times are curl's total time, measured from the client.

| Trial | HTTP | Seconds | Error | Warning recorded | Item | Fit card |
|---|---|---|---|---|---|---|
| 1 | 200 | 11.33 | none | yes: size XS dropped | 90s Track Jacket — Navy/White Stripe | yes |
| 2 | 200 | 12.33 | none | yes: size XS dropped | 90s Track Jacket — Navy/White Stripe | yes |
| 3 | 200 | 13.56 | none | yes: size XS dropped | 90s Track Jacket — Navy/White Stripe | yes |

Extra measurement, not one of the three trials: the first `/ask` request after
a `GET /`, which had returned in 0.22s, took 29.29s
(`rescue_first_request_29s.json`). The instance was already awake, so this is a
warm request, and it is over the 20-second target. Its cause is not known from
these files; the Render log for that time would show it.

Render's own log holds the server-side `[runlog]` records for these requests.
Those are not copied here yet.
