#!/bin/bash
# Scenario batch 3: the remaining DREAM standard shocks (27), sequential, checkpointed. Run detached on the box:
#   nohup bash cloud/run_batch3.sh > batch2.log 2>&1 &
# Safe to relaunch after any kill — every scenario resumes from its last converged stage.
set -uo pipefail
cd "$(dirname "$0")/../etl"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1
# NB: no FREESOLVER_BACKEND override (and no OPENBLAS/OMP_NUM_THREADS). Keeping pardiso first in
# the chain makes pypardiso load MKL, which UMFPACK's BLAS then runs on in parallel; with the
# override the process ran single-threaded on kvxopt's serial OpenBLAS: 1400–2700 s per
# factorization (batch2.log, 2026-08-25) versus 330–680 s (run6.log) on the same box.
# Shared box: if memory runs out, the kernel should kill the (resumable) solver, not Dokploy.
echo 1000 > /proc/self/oom_score_adj 2>/dev/null || true

# --from-year 2030 = DREAM's shock_year: 2030 is the first solved year and 2029 stays at the reference
# (DREAM's fixed t0). Batches 2-4 were run with --from-year 2029, which solved 2029 as a free year and
# made every 2030 shock anticipated by one year (makroskop-7cd); re-runs must use 2030.
run() {
  local out="$1"; shift
  if [ -f "shock_gdx/$out" ]; then echo "SKIP $out (already exported)"; return; fi
  echo "=============================================================="
  echo "SCENARIO $out"
  echo "=============================================================="
  uv run python freesolver.py solve-export --from-year 2030 "$@" --out "shock_gdx/$out" \
    || echo "FAILED: $out (continuing with the rest)"
}

# Validation-table shocks first (DREAM's finanspolitiske multiplikatorer), then the rest of the catalogue.
run Offentlig_varekoeb_ufin.gdx           --shock-name "qR(off,*)" --shock-years 2030-2129 --shock-factor 1.01
run Offentlig_Beskaeftigelse_ufin.gdx     --shock-name "hL(off,*)" --shock-years 2030-2129 --shock-factor 1.01
run Offentlige_investeringer_ufin.gdx     --shock-name "qI_s(!iTot,off,*)" --shock-years 2030-2129 --shock-factor 1.01
run Offentlig_loen_ufin.gdx               --shock-name "qProd(off,*)" --shock-years 2030-2129 --shock-factor 1.01
run Ikke_skattepligtig_indkomstoverforsel_ufin.gdx --shock-name "uvOvfSats(boernyd|boligyd|iskatpl|groen|lumpsumovf,*)" --shock-years 2030-2129 --shock-factor 1.01
run Overforsel_privat_ufin.gdx            --shock-name vOffTilHhRest --shock-years 2030-2129 --shock-delta 10.0
run Grundskyld_ufin.gdx                   --shock-name tGrund --shock-years 2030-2129 --shock-factor 1.10
run Vaegtafgift_ufin.gdx                  --shock-name utHhVaegt --shock-years 2030-2129 --shock-factor 1.10
run Aktieskat_ufin.gdx                    --shock-name tAktieTop --shock-years 2030-2129 --shock-delta 0.01
run Moms_ufin.gdx                         --shock-name "tMoms_y,tMoms_m" --shock-years 2030-2129 --shock-delta 0.005   # +1 pp hits a model boundary (qBolig(18) -> 0 around 2110) at share 0.93
run Registreringsafgift_ufin.gdx          --shock-name "tReg_y,tReg_m" --shock-years 2030-2129 --shock-factor 1.10
run Energiafgift_ufin.gdx                 --shock-name "tAfg_y(cEne,*,*),tAfg_m(cEne,*,*)" --shock-years 2030-2129 --shock-factor 1.10
run Forbrugsafgift_ufin.gdx               --shock-name "tAfg_y(cVar,*,*),tAfg_m(cVar,*,*)" --shock-years 2030-2129 --shock-factor 1.10
run Afgift_erhverv_ufin.gdx               --shock-name "tAfg_y(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*),tAfg_m(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*)" --shock-years 2030-2129 --shock-factor 1.10
run Produktsubsidier_ufin.gdx             --shock-name "rSub_y,rSub_m" --shock-years 2030-2129 --shock-factor 1.10
run Lontilskud_ufin.gdx                   --shock-name "rSubLoen(!tot,*)" --shock-years 2030-2129 --shock-factor 1.10
run Produktionssubsidier_ufin.gdx         --shock-name "rSubYRest(!tot,*)" --shock-years 2030-2129 --shock-factor 1.10
run Importpris_ufin.gdx                   --shock-name pM --shock-years 2030-2129 --shock-factor 1.01
run Eksportkonkurrerende_priser_ufin.gdx  --shock-name pXUdl --shock-years 2030-2129 --shock-factor 1.01
run Udenlandske_priser_ufin.gdx           --shock-name "pM,pXUdl" --shock-years 2030-2129 --shock-factor 1.01
# Labour supply: DREAM's exo/endo swaps (standard_shocks.gms). uDeltag/uh are DISUTILITY
# parameters (shLHh = 1/uh; uDeltag on the cost side of the participation FOC), so scaling
# them up LOWERS labour supply — the first batch-3 runs had the wrong sign (makroskop-6wz).
run Arbejdsudbud_beskaeftigelse_ufin.gdx  --shock-name snLHh --endogenize uDeltag --shock-years 2030-2129 --shock-factor 1.01
run Arbejdsudbud_timer_ufin.gdx           --shock-name uh --shock-years 2030-2129 --shock-factor 0.99009900990099   # = 1/1.01 -> shLHh +1 pct. exactly
run ArbejdsProd_ufin.gdx                  --shock-name "qProdHh_t,qProdxDK" --shock-years 2030-2129 --shock-factor 1.01
run VirkDisk_ufin.gdx                     --shock-name "rVirkDiskPrem(!spTot,*)" --shock-years 2030-2129 --shock-delta 0.001
run BoligRisiko_ufin.gdx                  --shock-name rBoligPrem --shock-years 2030-2129 --shock-delta 0.001
run AktieAfkast_ufin.gdx                  --shock-name "rVirkDiskPrem(!spTot,*),rAktieDriftPrem" --shock-years 2030-2129 --shock-delta 0.001
run RisikoPraemier_ufin.gdx               --shock-name "rVirkDiskPrem(!spTot,*),rAktieDriftPrem,rBoligPrem" --shock-years 2030-2129 --shock-delta 0.001
run Diskontering_ufin.gdx                 --shock-name jfDisk_t --shock-years 2030-2129 --shock-delta -0.001
run Loen_ufin.gdx                         --shock-name rLoenNash --shock-years 2030-2129 --shock-delta -0.01

echo "BATCH 3 DONE"
