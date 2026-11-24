alter table public.profils
  add column contact text check (char_length(contact) <= 100);

revoke select on public.profils from authenticated;
grant select (id, pseudo, cree_le) on public.profils to authenticated;
grant update (contact) on public.profils to authenticated;

create index collection_carte_foil_idx on public.collection (carte_id, foil);

create function public.mon_contact()
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select contact from public.profils where id = (select auth.uid())
$$;

create function public.echanges_possibles()
returns table (
  pseudo text,
  contact text,
  carte_id text,
  foil boolean,
  sens text,
  nombre integer
)
language sql
stable
security definer
set search_path = ''
as $$
  select p.pseudo, p.contact, autre.carte_id, autre.foil, 'recevoir', autre.a_echanger
  from public.collection as moi
  join public.collection as autre
    on autre.carte_id = moi.carte_id and autre.foil = moi.foil
  join public.profils as p on p.id = autre.user_id
  where moi.user_id = (select auth.uid())
    and moi.recherche
    and autre.a_echanger > 0
    and autre.user_id <> moi.user_id

  union all

  select p.pseudo, p.contact, autre.carte_id, autre.foil, 'donner', moi.a_echanger
  from public.collection as moi
  join public.collection as autre
    on autre.carte_id = moi.carte_id and autre.foil = moi.foil
  join public.profils as p on p.id = autre.user_id
  where moi.user_id = (select auth.uid())
    and moi.a_echanger > 0
    and autre.recherche
    and autre.user_id <> moi.user_id
$$;

revoke execute on function public.mon_contact() from public, anon;
grant execute on function public.mon_contact() to authenticated;
revoke execute on function public.echanges_possibles() from public, anon;
grant execute on function public.echanges_possibles() to authenticated;