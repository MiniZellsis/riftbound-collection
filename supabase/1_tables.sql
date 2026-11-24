create table public.profils (
  id uuid primary key references auth.users (id) on delete cascade,
  pseudo text not null unique check (char_length(pseudo) between 3 and 20),
  cree_le timestamptz not null default now()
);

create table public.collection (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  carte_id text not null,
  foil boolean not null default false,
  quantite integer not null default 0 check (quantite >= 0),
  a_echanger integer not null default 0 check (a_echanger >= 0),
  recherche boolean not null default false,
  constraint echange_possible check (a_echanger <= quantite),
  unique (user_id, carte_id, foil)
);

alter table public.profils enable row level security;
alter table public.collection enable row level security;

revoke all on public.profils, public.collection from anon, authenticated;
grant select, update (pseudo) on public.profils to authenticated;
grant select, insert, update, delete on public.collection to authenticated;

create policy "Les membres connectés voient les pseudos"
  on public.profils for select to authenticated
  using (true);

create policy "Chacun modifie seulement son profil"
  on public.profils for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

create policy "Lire sa collection"
  on public.collection for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "Ajouter dans sa collection"
  on public.collection for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "Modifier sa collection"
  on public.collection for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Supprimer de sa collection"
  on public.collection for delete to authenticated
  using ((select auth.uid()) = user_id);

create function public.creer_profil()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profils (id, pseudo)
  values (new.id, new.raw_user_meta_data ->> 'pseudo');
  return new;
end;
$$;

revoke execute on function public.creer_profil() from public, anon, authenticated;

create trigger creer_profil_apres_inscription
  after insert on auth.users
  for each row execute function public.creer_profil();
