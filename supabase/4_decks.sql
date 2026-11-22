create table public.decks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  nom text not null check (char_length(nom) between 1 and 60),
  monte boolean not null default false,
  cree_le timestamptz not null default now()
);

create index decks_du_joueur on public.decks (user_id);

create table public.deck_cartes (
  deck_id uuid not null references public.decks (id) on delete cascade,
  zone text not null check (zone in ('legende', 'champion', 'principal', 'arenes', 'runes', 'reserve')),
  carte_id text not null,
  quantite smallint not null check (quantite between 1 and 99),
  primary key (deck_id, zone, carte_id)
);

alter table public.decks enable row level security;
alter table public.deck_cartes enable row level security;

revoke all on public.decks, public.deck_cartes from anon, authenticated;
grant select, insert, update, delete on public.decks, public.deck_cartes to authenticated;

create policy "Lire ses decks"
  on public.decks for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "Créer ses decks"
  on public.decks for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "Modifier ses decks"
  on public.decks for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Supprimer ses decks"
  on public.decks for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy "Lire les cartes de ses decks"
  on public.deck_cartes for select to authenticated
  using (exists (
    select 1 from public.decks
    where decks.id = deck_id and decks.user_id = (select auth.uid())
  ));

create policy "Ajouter des cartes à ses decks"
  on public.deck_cartes for insert to authenticated
  with check (exists (
    select 1 from public.decks
    where decks.id = deck_id and decks.user_id = (select auth.uid())
  ));

create policy "Changer les cartes de ses decks"
  on public.deck_cartes for update to authenticated
  using (exists (
    select 1 from public.decks
    where decks.id = deck_id and decks.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1 from public.decks
    where decks.id = deck_id and decks.user_id = (select auth.uid())
  ));

create policy "Retirer des cartes de ses decks"
  on public.deck_cartes for delete to authenticated
  using (exists (
    select 1 from public.decks
    where decks.id = deck_id and decks.user_id = (select auth.uid())
  ));
