# Fixtures

`site/` is invented: Halvard Instruments and the Kestrel products do not exist. `questions.json` was written by this project. Passing them says the plumbing works and says nothing about the hidden Match 4 set.

`fake_script.json` is the hand-written reply script for the stub backend. It deliberately proposes wrong candidates alongside right ones (a withdrawn value, a near-miss row, a fabricated span, a value from page text addressed to the model), so the plain-code checks have something to reject. It shows what those checks do with those inputs. It does not show what a real model would propose.

Two faults cannot live in git, so `tools/selfcheck_m4.py` creates them on a temporary copy: `vendor/k7-unit-pricing.html` set to mode 000 and an empty `archive/` directory. Git does keep the corrupt `.pdf`, the binary `.dat`, the truncated HTML and the wrong-encoding page. HTTP faults (500, redirect loop, slow response, oversized page) come from `tools/fixture_server.py`.
