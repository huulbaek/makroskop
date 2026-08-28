#!/bin/bash
# Scenario batch 4: DREAM's financed variants (_perm) of all 38 standard shocks, sequential,
# checkpointed. Run detached on the box:
#   setsid nohup bash cloud/run_batch4.sh > batch4.log 2>&1 < /dev/null &
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

run() {
  local out="$1"; shift
  if [ -f "shock_gdx/$out" ]; then echo "SKIP $out (already exported)"; return; fi
  echo "=============================================================="
  echo "SCENARIO $out"
  echo "=============================================================="
  uv run python freesolver.py solve-export --from-year 2029 "$@" --out "shock_gdx/$out" \
    || echo "FAILED: $out (continuing with the rest)"
}

# Validation-table shocks first (DREAM's finanspolitiske multiplikatorer), then the rest of the catalogue.

# Batch 4: DREAM's financed variants (_perm). --closure tax-reaction frees the lukkeskat
# revenue vtLukning(tot,t), holds tLukning constant from 2030 and pins public net worth/GDP
# at 2129 to the reference (shock_template.gms B_fiscal_reaction). Same shocks as batches 1-3.
run Rente_perm.gdx                        --shock-name rRenteECB --shock-years 2030-2129 --shock-delta 0.01 --closure tax-reaction
run Bundskat_perm.gdx                        --shock-name tBund      --shock-years 2030-2129 --shock-delta 0.01 --closure tax-reaction
run AM_bidrag_perm.gdx                       --shock-name tAMbidrag  --shock-years 2030-2129 --shock-delta 0.01 --closure tax-reaction
run Selskabsskat_perm.gdx                    --shock-name tSelskab   --shock-years 2030-2129 --shock-delta 0.01 --closure tax-reaction
run Ejendomsvaerdiskat_perm.gdx              --shock-name tEjd       --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Offentligt_forbrug_perm.gdx              --shock-name "qR(off,*),qE(off,*),hL(off,*),qI_s(!iTot,off,*)" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Skattepligtig_indkomstoverforsel_perm.gdx --shock-name "uvOvfSats(!boernyd|boligyd|iskatpl|groen|lumpsumovf,*)" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Eksportmarkedsvaekst_perm.gdx            --shock-name uXMarked   --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Befolkning_perm.gdx                      --shock-name nPop       --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Offentlig_varekoeb_perm.gdx           --shock-name "qR(off,*)" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Offentlig_Beskaeftigelse_perm.gdx     --shock-name "hL(off,*)" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Offentlige_investeringer_perm.gdx     --shock-name "qI_s(!iTot,off,*)" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Offentlig_loen_perm.gdx               --shock-name "qProd(off,*)" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Ikke_skattepligtig_indkomstoverforsel_perm.gdx --shock-name "uvOvfSats(boernyd|boligyd|iskatpl|groen|lumpsumovf,*)" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Overforsel_privat_perm.gdx            --shock-name vOffTilHhRest --shock-years 2030-2129 --shock-delta 10.0 --closure tax-reaction
run Grundskyld_perm.gdx                   --shock-name tGrund --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Vaegtafgift_perm.gdx                  --shock-name utHhVaegt --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Aktieskat_perm.gdx                    --shock-name tAktieTop --shock-years 2030-2129 --shock-delta 0.01 --closure tax-reaction
run Moms_perm.gdx                         --shock-name "tMoms_y,tMoms_m" --shock-years 2030-2129 --shock-delta 0.005 --closure tax-reaction
run Registreringsafgift_perm.gdx          --shock-name "tReg_y,tReg_m" --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Energiafgift_perm.gdx                 --shock-name "tAfg_y(cEne,*,*),tAfg_m(cEne,*,*)" --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Forbrugsafgift_perm.gdx               --shock-name "tAfg_y(cVar,*,*),tAfg_m(cVar,*,*)" --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Afgift_erhverv_perm.gdx               --shock-name "tAfg_y(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*),tAfg_m(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*)" --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Produktsubsidier_perm.gdx             --shock-name "rSub_y,rSub_m" --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Lontilskud_perm.gdx                   --shock-name "rSubLoen(!tot,*)" --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Produktionssubsidier_perm.gdx         --shock-name "rSubYRest(!tot,*)" --shock-years 2030-2129 --shock-factor 1.10 --closure tax-reaction
run Importpris_perm.gdx                   --shock-name pM --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Eksportkonkurrerende_priser_perm.gdx  --shock-name pXUdl --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Udenlandske_priser_perm.gdx           --shock-name "pM,pXUdl" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Arbejdsudbud_beskaeftigelse_perm.gdx  --shock-name snLHh --endogenize uDeltag --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run Arbejdsudbud_timer_perm.gdx           --shock-name uh --shock-years 2030-2129 --shock-factor 0.99009900990099 --closure tax-reaction
run ArbejdsProd_perm.gdx                  --shock-name "qProdHh_t,qProdxDK" --shock-years 2030-2129 --shock-factor 1.01 --closure tax-reaction
run VirkDisk_perm.gdx                     --shock-name "rVirkDiskPrem(!spTot,*)" --shock-years 2030-2129 --shock-delta 0.001 --closure tax-reaction
run BoligRisiko_perm.gdx                  --shock-name rBoligPrem --shock-years 2030-2129 --shock-delta 0.001 --closure tax-reaction
run AktieAfkast_perm.gdx                  --shock-name "rVirkDiskPrem(!spTot,*),rAktieDriftPrem" --shock-years 2030-2129 --shock-delta 0.001 --closure tax-reaction
run RisikoPraemier_perm.gdx               --shock-name "rVirkDiskPrem(!spTot,*),rAktieDriftPrem,rBoligPrem" --shock-years 2030-2129 --shock-delta 0.001 --closure tax-reaction
run Diskontering_perm.gdx                 --shock-name jfDisk_t --shock-years 2030-2129 --shock-delta -0.001 --closure tax-reaction
run Loen_perm.gdx                         --shock-name rLoenNash --shock-years 2030-2129 --shock-delta -0.01 --closure tax-reaction
