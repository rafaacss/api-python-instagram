<template>
  <section class="w-full">
    <!-- Header opcional -->
    <header v-if="title" class="mb-3 flex items-center justify-between">
      <h2 class="text-xl font-semibold">{{ title }}</h2>
      <a v-if="instagramUrl" :href="instagramUrl" target="_blank" rel="noopener" class="text-sm underline hover:no-underline">Ver no Instagram</a>
    </header>

    <!-- Carrossel de thumbs -->
    <div
      ref="scroller"
      class="relative flex gap-3 overflow-x-auto scroll-smooth snap-x snap-mandatory pb-2"
      :class="[{ 'pr-10': showPeek }]"
      @keydown.left.prevent="scrollBy(-1)"
      @keydown.right.prevent="scrollBy(1)"
      tabindex="0"
      role="list"
      aria-label="Feed do Instagram"
    >
      <article
        v-for="(post, idx) in posts"
        :key="post.id"
        role="listitem"
        class="relative min-w-[160px] max-w-[220px] shrink-0 snap-start"
      >
        <button
          class="group block w-full focus:outline-none"
          @click="openModal(idx, 0)"
          :aria-label="`Abrir publicação ${idx + 1}`"
        >
          <div class="relative aspect-square w-full overflow-hidden rounded-2xl bg-gray-100">
            <!-- Imagem / vídeo thumb -->
            <img
              v-if="thumbUrl(post)"
              class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              :src="thumbUrl(post)"
              :alt="altText(post)"
              loading="lazy"
              decoding="async"
            />
            <div v-else class="flex h-full w-full items-center justify-center text-sm text-gray-500">
              sem mídia
            </div>

            <!-- Badges -->
            <div class="pointer-events-none absolute right-2 top-2 flex items-center gap-1">
              <span v-if="post.media_type === 'VIDEO'" class="rounded bg-black/70 px-2 py-0.5 text-xs text-white">Vídeo</span>
              <span v-else-if="post.media_type?.startsWith('CAROUSEL') || post.children?.length" class="rounded bg-black/70 px-2 py-0.5 text-xs text-white">Carrossel</span>
            </div>
          </div>
        </button>

        <!-- Legenda curta -->
        <p v-if="showCaptions && post.caption" class="mt-2 line-clamp-2 text-sm text-gray-700">{{ post.caption }}</p>
      </article>
    </div>

    <!-- Controles do carrossel -->
    <div class="mt-3 flex items-center justify-between">
      <div class="flex gap-2">
        <button class="rounded-xl border px-3 py-1 text-sm hover:bg-gray-50" @click="scrollBy(-1)">⟵</button>
        <button class="rounded-xl border px-3 py-1 text-sm hover:bg-gray-50" @click="scrollBy(1)">⟶</button>
      </div>
      <div class="text-xs text-gray-500">{{ posts.length }} publicações</div>
    </div>

    <!-- Modal Viewer -->
    <transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" @keydown.esc="closeModal" @click.self="closeModal">
        <div class="relative grid w-full max-w-5xl grid-cols-1 gap-0 overflow-hidden rounded-2xl bg-white shadow-2xl md:grid-cols-[minmax(0,1fr)_380px]">
          <!-- Mídia principal -->
          <div class="relative bg-black">
            <button class="absolute left-2 top-2 z-10 rounded-full bg-black/60 p-2 text-white" @click="closeModal" aria-label="Fechar">
              ✕
            </button>

            <!-- Navegação entre posts -->
            <button class="absolute left-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/60 p-2 text-white" @click.stop="prev()" aria-label="Anterior">⟵</button>
            <button class="absolute right-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/60 p-2 text-white" @click.stop="next()" aria-label="Próximo">⟶</button>

            <!-- Container da mídia (imagem, vídeo ou carrossel interno) -->
            <div class="flex aspect-square w-full items-center justify-center md:aspect-[4/3]">
              <!-- Se for carrossel, mostra o item atual -->
              <template v-if="currentIsCarousel">
                <div class="relative h-full w-full">
                  <component :is="mediaComponent(currentChild)" :item="currentChild" class="h-full w-full" />

                  <!-- mini navegação dos itens do carrossel -->
                  <div class="absolute bottom-2 left-1/2 z-10 flex -translate-x-1/2 gap-2 rounded-full bg-black/50 px-2 py-1">
                    <button
                      v-for="(child, cIdx) in currentPost.children"
                      :key="child.id || cIdx"
                      class="h-2 w-2 rounded-full"
                      :class="cIdx === childIndex ? 'bg-white' : 'bg-white/40'"
                      @click="childIndex = cIdx"
                      aria-label="Ir para mídia do carrossel"
                    />
                  </div>
                </div>
              </template>
              <template v-else>
                <component :is="mediaComponent(currentPost)" :item="currentPost" class="h-full w-full" />
              </template>
            </div>
          </div>

          <!-- Lateral com caption/contas -->
          <aside class="flex max-h-[90vh] flex-col gap-4 overflow-y-auto p-5">
            <header class="flex items-center justify-between">
              <h3 class="text-lg font-semibold">Publicação</h3>
              <a v-if="currentPost.permalink" :href="currentPost.permalink" target="_blank" rel="noopener" class="rounded-lg border px-3 py-1 text-sm hover:bg-gray-50">Abrir no Instagram ↗</a>
            </header>

            <div class="space-y-3 text-sm text-gray-700">
              <p v-if="currentPost.caption" class="whitespace-pre-wrap">{{ currentPost.caption }}</p>
              <div v-if="currentPost.timestamp" class="text-xs text-gray-500">{{ formatDate(currentPost.timestamp) }}</div>
              <div class="flex flex-wrap gap-3 text-xs text-gray-600">
                <div v-if="currentPost.like_count">❤️ {{ currentPost.like_count }}</div>
                <div v-if="currentPost.comments_count">💬 {{ currentPost.comments_count }}</div>
              </div>
            </div>

            <!-- Miniaturas dentro do modal para pular de post -->
            <div class="mt-2 grid grid-cols-6 gap-2">
              <button
                v-for="(p, i) in posts"
                :key="p.id + '-thumb-modal'"
                class="group relative aspect-square overflow-hidden rounded-lg border"
                :class="i === index ? 'ring-2 ring-black' : ''"
                @click="go(i)"
                :aria-label="`Ir para publicação ${i + 1}`"
              >
                <img :src="thumbUrl(p)" :alt="altText(p)" class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
              </button>
            </div>
          </aside>
        </div>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

type IgMediaType = 'IMAGE' | 'VIDEO' | 'CAROUSEL_ALBUM' | string

interface IgChildItem {
  id: string
  media_type: IgMediaType
  media_url?: string
  thumbnail_url?: string
  permalink?: string
}

interface IgPostItem {
  id: string
  caption?: string
  media_type: IgMediaType
  media_url?: string
  thumbnail_url?: string
  permalink?: string
  timestamp?: string
  children?: IgChildItem[]
  like_count?: number
  comments_count?: number
}

interface Props {
  apiUrl: string
  title?: string
  instagramUrl?: string
  showCaptions?: boolean
  showPeek?: boolean
  /** Quantos itens pré-carregar (lazy permanece para imagens) */
  preload?: number
}

const props = defineProps<Props>()

const posts = ref<IgPostItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const scroller = ref<HTMLDivElement | null>(null)

// Modal state
const isOpen = ref(false)
const index = ref(0)
const childIndex = ref(0)

const currentPost = computed(() => posts.value[index.value] || ({} as IgPostItem))
const currentIsCarousel = computed(() => !!(currentPost.value?.children?.length))
const currentChild = computed(() => currentPost.value?.children?.[childIndex.value])

function normalize(item: any): IgPostItem {
  // Mapeamento específico para o endpoint https://api-instagram.redbeauty.com.br/api/instagram/posts
  // Formatos previstos:
  // 1) { data: [ { id, caption, media_type, media_url, thumbnail_url, permalink, timestamp, children: { data: [...] } } ] }
  // 2) [ { ... o mesmo objeto ... } ]
  const childrenArr = Array.isArray(item?.children?.data)
    ? item.children.data
    : (Array.isArray(item?.children) ? item.children : [])

  return {
    id: String(item.id),
    caption: item.caption ?? '',
    media_type: item.media_type || item.type || 'IMAGE',
    media_url: item.media_url || item.media || item.url || undefined,
    thumbnail_url: item.thumbnail_url || item.thumbnail || item.media_url || undefined,
    permalink: item.permalink || item.link || undefined,
    timestamp: item.timestamp || item.taken_at || item.created_time || undefined,
    children: childrenArr?.map((c: any) => ({
      id: String(c.id ?? c.pk ?? Math.random().toString(36).slice(2)),
      media_type: c.media_type || c.type || 'IMAGE',
      media_url: c.media_url || c.media || c.url || undefined,
      thumbnail_url: c.thumbnail_url || c.thumbnail || c.media_url || undefined,
      permalink: c.permalink || c.link || undefined,
    })),
    like_count: item.like_count ?? item.likes ?? undefined,
    comments_count: item.comments_count ?? item.comments ?? undefined,
  }
}

async function fetchPosts() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(props.apiUrl, { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    // Aceita { data: [...] } ou array direto
    const arr = Array.isArray((data as any)?.data) ? (data as any).data : (Array.isArray(data) ? data : [])
    posts.value = arr.map(normalize)
  } catch (e: any) {
    error.value = e?.message || 'Falha ao carregar'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchPosts()
})

function thumbUrl(p: IgPostItem | IgChildItem | undefined) {
  if (!p) return ''
  return (p as IgPostItem).thumbnail_url || (p as IgPostItem).media_url || ''
}

function altText(p: IgPostItem | IgChildItem | undefined) {
  if (!p) return 'Publicação do Instagram'
  const c = (p as IgPostItem).caption
  return c ? String(c).slice(0, 100) : 'Publicação do Instagram'
}

function openModal(postIdx: number, childIdx = 0) {
  index.value = postIdx
  childIndex.value = childIdx
  isOpen.value = true
  // Trava o scroll do body
  document.documentElement.classList.add('overflow-hidden')
}

function closeModal() {
  isOpen.value = false
  document.documentElement.classList.remove('overflow-hidden')
}

function go(i: number) {
  index.value = (i + posts.value.length) % posts.value.length
  childIndex.value = 0
}

function prev() { go(index.value - 1) }
function next() { go(index.value + 1) }

function scrollBy(dir: 1 | -1) {
  const el = scroller.value
  if (!el) return
  const card = el.querySelector<HTMLElement>('article')
  const delta = (card?.offsetWidth || 200) + 12 // gap aproximado
  el.scrollBy({ left: dir * delta, behavior: 'smooth' })
}

function formatDate(ts?: string) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(d)
  } catch { return ts }
}

watch(isOpen, (val) => {
  if (val) {
    // Navegação por teclado dentro do modal
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') prev()
      else if (e.key === 'ArrowRight') next()
      else if (e.key === 'Escape') closeModal()
    }
    window.addEventListener('keydown', onKey)
    const off = () => window.removeEventListener('keydown', onKey)
    const stop = watch(isOpen, (v) => { if (!v) off(); stop() })
  }
})

// Componentes internos: Image e Video com aspectos responsivos
const ImageMedia = {
  props: { item: { type: Object, required: true } },
  template: `
    <img :src="item.media_url || item.thumbnail_url" :alt="item.caption || 'Imagem'" class="h-full w-full object-contain" loading="eager" />
  `
}

const VideoMedia = {
  props: { item: { type: Object, required: true } },
  template: `
    <video class="h-full w-full" :poster="item.thumbnail_url" preload="metadata" controls playsinline>
      <source :src="item.media_url" type="video/mp4" />
      Seu navegador não suporta vídeo.
    </video>
  `
}

function mediaComponent(p?: IgPostItem | IgChildItem) {
  const type = p?.media_type || 'IMAGE'
  if (type.includes('VIDEO')) return VideoMedia
  return ImageMedia
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Utilitário para line-clamp se o projeto não tiver plugin */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
