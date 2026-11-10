"""Build a compact pokedata.json for the Pokédex app from PokeAPI CSV tables."""
import csv, json, sys, os, re
from collections import defaultdict

SRC = sys.argv[1]
OUT = sys.argv[2]
EN = '9'

def rows(name):
    with open(os.path.join(SRC, name + '.csv'), newline='', encoding='utf-8') as f:
        yield from csv.DictReader(f)

def clean(t):
    return re.sub(r'\s+', ' ', t.replace('\f', ' ').replace('­', '')).strip()

# ---------- types ----------
types = {r['id']: r['identifier'] for r in rows('types') if int(r['id']) <= 18}
type_order = [types[str(i)] for i in range(1, 19)]
tidx = {t: i for i, t in enumerate(type_order)}
eff = [[1.0] * 18 for _ in range(18)]  # eff[attacker][defender]
for r in rows('type_efficacy'):
    a, d = r['damage_type_id'], r['target_type_id']
    if a in types and d in types:
        eff[tidx[types[a]]][tidx[types[d]]] = int(r['damage_factor']) / 100

# ---------- names ----------
species_name, genus = {}, {}
for r in rows('pokemon_species_names'):
    if r['local_language_id'] == EN:
        species_name[r['pokemon_species_id']] = r['name']
        genus[r['pokemon_species_id']] = r['genus']

form_pokemon_name = {}
form_by_pokemon_default = {}
for r in rows('pokemon_forms'):
    if r['is_default'] == '1':
        form_by_pokemon_default[r['pokemon_id']] = r['id']
for r in rows('pokemon_form_names'):
    if r['local_language_id'] == EN and r['pokemon_name']:
        form_pokemon_name[r['pokemon_form_id']] = r['pokemon_name']

# ---------- species ----------
species = {}
for r in rows('pokemon_species'):
    species[r['id']] = r

flavor = {}
best_ver = {}
for r in rows('pokemon_species_flavor_text'):
    if r['language_id'] != EN:
        continue
    v = int(r['version_id'])
    if v >= best_ver.get(r['species_id'], -1):
        best_ver[r['species_id']] = v
        flavor[r['species_id']] = clean(r['flavor_text'])

# ---------- abilities ----------
abil_name = {r['ability_id']: r['name'] for r in rows('ability_names') if r['local_language_id'] == EN}
abil_desc = {}
for r in rows('ability_prose'):
    if r['local_language_id'] == EN and r['short_effect']:
        abil_desc[r['ability_id']] = clean(r['short_effect'])
abil_flav, abil_flav_vg = {}, {}
for r in rows('ability_flavor_text'):
    if r['language_id'] != EN:
        continue
    vg = int(r['version_group_id'])
    if vg >= abil_flav_vg.get(r['ability_id'], -1):
        abil_flav_vg[r['ability_id']] = vg
        abil_flav[r['ability_id']] = clean(r['flavor_text'])
abilities_out = {}

poke_abil = defaultdict(list)
for r in rows('pokemon_abilities'):
    poke_abil[r['pokemon_id']].append((int(r['slot']), r['ability_id'], r['is_hidden'] == '1'))

# ---------- types / stats per pokemon ----------
poke_types = defaultdict(list)
for r in rows('pokemon_types'):
    if r['type_id'] in types:
        poke_types[r['pokemon_id']].append((int(r['slot']), types[r['type_id']]))
poke_stats = defaultdict(lambda: [0] * 6)
for r in rows('pokemon_stats'):
    s = int(r['stat_id'])
    if 1 <= s <= 6:
        poke_stats[r['pokemon_id']][s - 1] = int(r['base_stat'])

# ---------- moves ----------
move_name = {r['move_id']: r['name'] for r in rows('move_names') if r['local_language_id'] == EN}
dmg_class = {'1': 'status', '2': 'physical', '3': 'special'}
moves_meta = {}
for r in rows('moves'):
    if r['type_id'] not in types or r['id'] not in move_name:
        continue
    moves_meta[r['id']] = [move_name[r['id']], tidx[types[r['type_id']]], dmg_class.get(r['damage_class_id'], 'status'),
                           int(r['power']) if r['power'] else None, int(r['accuracy']) if r['accuracy'] else None,
                           int(r['pp']) if r['pp'] else None]

vg_label = {
    '27': 'Scarlet / Violet', '26': 'Scarlet / Violet', '25': 'Scarlet / Violet',
    '22': 'Sword / Shield', '21': 'Sword / Shield', '20': 'Sword / Shield',
    '23': 'Brilliant Diamond / Shining Pearl', '18': 'Ultra Sun / Ultra Moon', '17': 'Sun / Moon',
    '16': 'Omega Ruby / Alpha Sapphire', '15': 'X / Y', '14': 'Black 2 / White 2', '11': 'Black / White',
    '10': 'HeartGold / SoulSilver', '9': 'Platinum', '8': 'Diamond / Pearl', '7': 'FireRed / LeafGreen',
    '6': 'Emerald', '5': 'Ruby / Sapphire', '4': 'Crystal', '3': 'Gold / Silver', '2': 'Yellow', '1': 'Red / Blue',
    '24': 'Legends: Arceus', '30': 'Legends: Z-A', '31': 'Legends: Z-A', '19': "Let's Go", '32': 'Champions',
}
vg_pref = ['27', '26', '25', '22', '21', '20', '23', '18', '17', '16', '15', '14', '11', '10', '9', '8', '7', '6',
           '5', '4', '3', '2', '1', '30', '31', '24', '19', '32']
rank = {v: i for i, v in enumerate(vg_pref)}
# level-up moves per pokemon per version group
lv = defaultdict(lambda: defaultdict(dict))  # pokemon -> vg -> move -> level
tm_count = defaultdict(lambda: defaultdict(set))
for r in rows('pokemon_moves'):
    if r['pokemon_move_method_id'] != '1' or r['version_group_id'] not in rank or r['move_id'] not in moves_meta:
        continue
    d = lv[r['pokemon_id']][r['version_group_id']]
    lvl = int(r['level'] or 0)
    m = r['move_id']
    if m not in d or lvl < d[m]:
        d[m] = lvl
used_moves = set()
poke_moves = {}
for pid, byvg in lv.items():
    vg = min(byvg, key=lambda v: rank[v])
    lst = sorted(byvg[vg].items(), key=lambda kv: (kv[1], moves_meta[kv[0]][0]))
    poke_moves[pid] = (vg_label[vg], [[int(m), l] for m, l in lst])
    used_moves.update(m for m, _ in lst)

# ---------- items, evolutions ----------
item_name = {r['item_id']: r['name'] for r in rows('item_names') if r['local_language_id'] == EN}
loc_name = {r['location_id']: r['name'] for r in rows('location_names') if r['local_language_id'] == EN}
trig = {r['id']: r['identifier'] for r in rows('evolution_triggers')}
evo_text = defaultdict(list)
for r in rows('pokemon_evolution'):
    t = trig.get(r['evolution_trigger_id'], '')
    parts = []
    if t == 'level-up':
        parts.append(f"Lv. {r['minimum_level']}" if r['minimum_level'] else 'Level up')
    elif t == 'trade':
        parts.append('Trade')
    elif t == 'use-item':
        parts.append(item_name.get(r['trigger_item_id'], 'Use item'))
    elif t == 'shed':
        parts.append('Level 20, empty slot')
    else:
        parts.append(t.replace('-', ' ').capitalize())
    if t == 'trade' and r['trade_species_id']:
        parts.append('for ' + species_name.get(r['trade_species_id'], ''))
    if r['held_item_id']:
        parts.append('holding ' + item_name.get(r['held_item_id'], 'item'))
    if r['minimum_happiness']:
        parts.append('high friendship')
    if r['minimum_affection']:
        parts.append('high affection')
    if r['minimum_beauty']:
        parts.append('high beauty')
    if r['time_of_day']:
        parts.append('at ' + r['time_of_day'])
    if r['known_move_id']:
        parts.append('knowing ' + move_name.get(r['known_move_id'], 'a move'))
    if r['known_move_type_id'] and r['known_move_type_id'] in types:
        parts.append('knowing a ' + types[r['known_move_type_id']].capitalize() + ' move')
    if r['location_id']:
        parts.append('at a special location')
    if r['gender_id'] == '1':
        parts.append('(female)')
    elif r['gender_id'] == '2':
        parts.append('(male)')
    if r['needs_overworld_rain'] == '1':
        parts.append('in rain')
    if r['turn_upside_down'] == '1':
        parts.append('console upside down')
    if r['party_species_id']:
        parts.append('with ' + species_name.get(r['party_species_id'], '') + ' in party')
    if r['party_type_id'] and r['party_type_id'] in types:
        parts.append('with a ' + types[r['party_type_id']].capitalize() + ' type in party')
    if r['relative_physical_stats'] == '1':
        parts.append('Atk > Def')
    elif r['relative_physical_stats'] == '-1':
        parts.append('Atk < Def')
    elif r['relative_physical_stats'] == '0':
        parts.append('Atk = Def')
    if r['used_move_id']:
        parts.append('after using ' + move_name.get(r['used_move_id'], 'a move'))
    if r['minimum_steps']:
        parts.append(f"after {r['minimum_steps']} steps")
    txt = ' '.join(p for p in parts if p).strip()
    if txt and txt not in evo_text[r['evolved_species_id']]:
        evo_text[r['evolved_species_id']].append(txt)

chains = defaultdict(list)
for sid, s in species.items():
    chains[s['evolution_chain_id']].append(sid)
chains_out = {}
for cid, sids in chains.items():
    if len(sids) < 2:
        continue
    chains_out[cid] = [[int(s), int(species[s]['evolves_from_species_id'] or 0), ' / '.join(evo_text.get(s, []))]
                       for s in sorted(sids, key=lambda x: int(species[x]['order']))]

# ---------- pokemon ----------
pokemon_out = []
for r in rows('pokemon'):
    pid, sid = r['id'], r['species_id']
    if sid not in species or not poke_types.get(pid):
        continue
    sp = species[sid]
    name = species_name.get(sid, r['identifier'].title())
    if r['is_default'] != '1':
        fid = form_by_pokemon_default.get(pid)
        name = form_pokemon_name.get(fid) or r['identifier'].replace('-', ' ').title()
    ab = []
    for slot, aid, hidden in sorted(poke_abil[pid]):
        abilities_out[aid] = [abil_name.get(aid, aid), abil_desc.get(aid) or abil_flav.get(aid, '')]
        ab.append([int(aid), 1 if hidden else 0])
    mv = poke_moves.get(pid)
    flags = (1 if sp['is_legendary'] == '1' else 0) | (2 if sp['is_mythical'] == '1' else 0) | (4 if sp['is_baby'] == '1' else 0)
    pokemon_out.append({
        'i': int(pid), 's': int(sid), 'n': name, 'k': r['identifier'],
        't': [tidx[t] for _, t in sorted(poke_types[pid])],
        'b': poke_stats[pid], 'h': int(r['height']), 'w': int(r['weight']),
        'a': ab, 'd': 1 if r['is_default'] == '1' else 0,
        'g': int(sp['generation_id']), 'f': flags,
        'c': int(sp['evolution_chain_id']) if sp['evolution_chain_id'] else 0,
        'cr': int(sp['capture_rate']) if sp['capture_rate'] else None,
        'gr': int(sp['gender_rate']),
        **({'mv': mv[0], 'm': mv[1]} if mv else {}),
    })

species_out = {int(s): [species_name.get(s, ''), genus.get(s, ''), flavor.get(s, '')] for s in species}

data = {
    'types': type_order,
    'eff': eff,
    'pokemon': pokemon_out,
    'species': species_out,
    'abilities': {int(k): v for k, v in abilities_out.items()},
    'moves': {int(k): v for k, v in moves_meta.items() if k in used_moves},
    'chains': {int(k): v for k, v in chains_out.items()},
    'source': 'PokeAPI (github.com/PokeAPI/pokeapi), built 2026-11-11',
}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
print('pokemon', len(pokemon_out), 'species', len(species_out), 'moves', len(data['moves']),
      'chains', len(chains_out), 'bytes', os.path.getsize(OUT))
