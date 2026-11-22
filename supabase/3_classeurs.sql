create table public.classeurs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  nom text not null check (char_length(nom) between 1 and 40),
  colonnes smallint not null check (colonnes between 1 and 6),
  lignes smallint not null check (lignes between 1 and 6),
  pages smallint not null check (pages between 1 and 400),
  couleur text not null default 'nuit' check (char_length(couleur) between 1 and 20),
  cree_le timestamptz not null default now()
);

create index classeurs_du_joueur on public.classeurs (user_id);

create table public.classeur_pochettes (
  classeur_id uuid not null references public.classeurs (id) on delete cascade,
  pochette integer not null check (pochette between 0 and 14399),
  carte_id text not null,
  version text not null default 'toutes' check (version in ('toutes', 'normale', 'foil')),
  primary key (classeur_id, pochette)
);

alter table public.classeurs enable row level security;
alter table public.classeur_pochettes enable row level security;

revoke all on public.classeurs, public.classeur_pochettes from anon, authenticated;
grant select, insert, update, delete on public.classeurs, public.classeur_pochettes to authenticated;

create policy "Lire ses classeurs"
  on public.classeurs for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "Créer ses classeurs"
  on public.classeurs for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "Modifier ses classeurs"
  on public.classeurs for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Supprimer ses classeurs"
  on public.classeurs for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy "Lire les pochettes de ses classeurs"
  on public.classeur_pochettes for select to authenticated
  using (exists (
    select 1 from public.classeurs
    where classeurs.id = classeur_id and classeurs.user_id = (select auth.uid())
  ));

create policy "Remplir les pochettes de ses classeurs"
  on public.classeur_pochettes for insert to authenticated
  with check (exists (
    select 1 from public.classeurs
    where classeurs.id = classeur_id and classeurs.user_id = (select auth.uid())
  ));

create policy "Changer les pochettes de ses classeurs"
  on public.classeur_pochettes for update to authenticated
  using (exists (
    select 1 from public.classeurs
    where classeurs.id = classeur_id and classeurs.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1 from public.classeurs
    where classeurs.id = classeur_id and classeurs.user_id = (select auth.uid())
  ));

create policy "Vider les pochettes de ses classeurs"
  on public.classeur_pochettes for delete to authenticated
  using (exists (
    select 1 from public.classeurs
    where classeurs.id = classeur_id and classeurs.user_id = (select auth.uid())
  ));
