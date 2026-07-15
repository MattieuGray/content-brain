#!/usr/bin/env bash
# e2e_tag.sh - end-to-end check of the tagging pass against a fake vault.
# Requires the `claude` CLI installed and logged in. Costs a few cents.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$(cd "$HERE/../plugins/content-brain/scripts" && pwd)"
TMP="$(mktemp -d)"
echo "temp vault: $TMP"

"$SCRIPTS/vault_init.sh" "$TMP" >/dev/null

SRC="$TMP/wiki/sources/articles"
mkdir -p "$SRC"

write_note() { printf '%s\n' "$2" > "$SRC/$1.md"; }

write_note "owner-financing-basics" "Owner financing lets a buyer purchase a business with a seller-held note instead of a bank loan. The seller carries the paper and collects payments over time."
write_note "seller-note-terms" "When you structure a seller note, the interest rate and term matter as much as price. A longer amortization lowers the monthly payment on the note."
write_note "exit-multiples" "Your exit multiple is set long before you sell. Buyers pay for clean books, recurring revenue, and a business that runs without the founder."
write_note "prepping-for-sale" "To prep a company for sale, remove yourself from operations, document the systems, and get the financials audited a year ahead of the exit."
write_note "using-leverage" "Leverage means using other people's money and time to control more than you could alone. Debt, partnerships, and teams are all forms of leverage."
write_note "delegation-leverage" "The highest form of leverage is people. Hire operators, give them ownership of outcomes, and multiply what one founder can do."
write_note "cold-plunge-morning" "My morning routine is a cold plunge, black coffee, and twenty minutes of reading before anyone else is awake."
write_note "favorite-tacos" "The best tacos in town are the al pastor off the truck on Fifth Street. Nothing about business here, just tacos."
write_note "mixed-financing-and-exit" "You can combine owner financing with an exit: sell the business, carry a note for part of the price, and keep income flowing after the sale."

STATE="$TMP/.content-brain/state.json"
cat > "$STATE" <<'JSON'
{ "vault_path": "PLACEHOLDER", "interview": { "pillars": ["Owner Financing", "Exits", "Leverage"] } }
JSON

SPEC="$TMP/.content-brain/tag_spec.json"
python3 -c "import json,sys; t=json.load(open(sys.argv[1])); s=json.load(open(sys.argv[2])); t['allowed_values']['pillars']=s['interview']['pillars']; json.dump(t, open(sys.argv[3],'w'), indent=2)" \
  "$SCRIPTS/specs/tag_spec.template.json" "$STATE" "$SPEC"

set +e
python3 "$SCRIPTS/corpus_pass.py" \
  --input "$TMP/wiki/sources/**/*.md" \
  --spec "$SPEC" \
  --out "$TMP/.content-brain/tags.csv" \
  --model haiku \
  --audit 3
RC=$?
set -e

echo "corpus_pass exit code: $RC (0 means reconciled)"
[ "$RC" -eq 0 ] || { echo "FAIL: run did not reconcile"; exit 1; }

echo "--- rows ---"
cat "$TMP/.content-brain/tags.csv"

# Spot-check: the obvious owner-financing note should carry the Owner Financing pillar.
if grep "owner-financing-basics" "$TMP/.content-brain/tags.csv" | grep -q "Owner Financing"; then
  echo "PASS: owner-financing-basics tagged Owner Financing"
else
  echo "WARN: owner-financing-basics did not get the expected pillar; inspect the rows above"
fi

echo "E2E_DONE $TMP"
