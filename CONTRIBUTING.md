# VikeSesh Contribution Notes

VikeSesh is comprised of a Next.JS frontend ([/frontend](./frontend)),
and a Flask backend ([/backend](./backend)).

## Frontend
The recommended package manager is `pnpm`.

Run `pnpm --filter frontend run dev` to launch the Next.JS dev server.

## Backend
`uv` is recommended as a package manager, but `pip` and virtual environments should work fine.

To launch the dev server, run `uv tool run -- flask --app=backend run --debug`,
or `flask --app=backend run --debug` if the Flask cli is in scope.
