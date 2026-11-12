# Concrete Reign — Claude integration handoff

Unrelated to the sports bot. It is stored here only because this cloud session can push to this repository alone.

- `concrete-reign-claude-integration.bundle`: incremental bundle (prerequisite `273b177`) holding branch
  `claude/city-sample-integration` at `c125643`.
- `patches/`: the same three commits as `git format-patch` files.

Apply in the Concrete Reign repo (which already contains `273b177` from the Phase 2 bundle):

```sh
git fetch /path/to/concrete-reign-claude-integration.bundle claude/city-sample-integration:claude/city-sample-integration
# or: git checkout -b claude/city-sample-integration 273b177 && git am patches/*.patch
```

Start with `docs/claude/PHASE2_VEHICLE_REVIEW.md` and `docs/claude/CITY_SAMPLE_INTEGRATION_REVIEW.md`.
