# PokéDex Pro

A fast, offline-friendly Pokémon reference app. All Pokémon data is saved inside the app (`pokedata.json`), so it doesn't depend on any API at runtime — only the images are loaded from the PokeAPI sprites project.

## Features

- **Search** every Pokémon by name or National Dex number (press `/` to jump to search)
- **Pokémon pages**: official artwork (with shiny toggle), types, base stats, abilities with descriptions, height/weight, gender ratio, catch rate, Pokédex entry, type weaknesses, evolution chain with methods, alternate forms/Megas, and level-up moves (sortable)
- **Types**: pick one type to see what it's super effective against and what it's weak to, or pick two for dual-type defence; full 18×18 type chart
- **Browse**: all 1,025 species (plus forms and Megas), filter by type and generation, sort by any stat
- **Compare**: two Pokémon side by side, with speed and same-type-attack matchups
- **Team Builder**: six slots, shared weaknesses and coverage gaps (saved in your browser)
- **Who's That Pokémon?**: silhouette quiz with streaks, filterable by generation
- **Favourites**, random Pokémon button, dark mode

## Hosting on GitHub Pages

1. Push `index.html` and `pokedata.json` to a repository.
2. Repository **Settings → Pages → Build and deployment → Deploy from a branch**, pick `main` and `/ (root)`.
3. The app is live at `https://<username>.github.io/<repo>/` within a minute or two.

## Updating the data

`pokedata.json` was built from the CSV tables in [PokeAPI/pokeapi](https://github.com/PokeAPI/pokeapi) (`data/v2/csv`) with `tools/build_data.py`:

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/PokeAPI/pokeapi.git
cd pokeapi && git sparse-checkout set data/v2/csv && cd ..
python3 tools/build_data.py pokeapi/data/v2/csv pokedata.json
```

Data: PokeAPI. Pokémon and related names are trademarks of Nintendo, Game Freak and The Pokémon Company. Fan project, not affiliated.
