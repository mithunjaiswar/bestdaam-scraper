create table if not exists public.products (
  id text primary key,
  name text not null,
  raw_name text,
  category text not null,
  category_key text,
  emoji text,
  image_url text,
  rating numeric,
  ratings_reviews text,
  last_updated date,
  catalog_data jsonb not null,
  synced_at timestamptz not null default now()
);

create table if not exists public.price_history (
  product_id text not null references public.products(id) on delete cascade,
  store text not null,
  observed_on date not null,
  price integer not null check (price > 0),
  source_url text,
  primary key (product_id, store, observed_on)
);

create index if not exists products_category_idx
  on public.products(category_key);

create index if not exists price_history_date_idx
  on public.price_history(observed_on desc);

alter table public.products enable row level security;
alter table public.price_history enable row level security;
