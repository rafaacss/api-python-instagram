<template>
  <div class="salon-container">
    <!-- Menu Lateral Flutuante -->
    <div class="salon-sidebar" :class="{ open: sidebarOpen }">
      <div class="salon-logo">RED Beauty</div>
      <nav>
        <ul class="salon-nav-menu">
          <li v-for="item in menuItems" :key="item.id">
            <a @click.prevent="scrollToSection(item.id)" href="#">{{ item.label }}</a>
          </li>
        </ul>
      </nav>
    </div>

    <!-- Botão Menu Mobile -->
    <button class="salon-menu-toggle" @click="toggleSidebar">☰</button>

    <!-- Hero Section -->
    <div class="salon-hero">
      <div class="salon-hero-content">
        <h1>Transforme sua Beleza</h1>
        <p>Descubra nossos serviços exclusivos e viva uma experiência única de cuidado e bem-estar</p>
        <button class="salon-cta-button" @click="scrollToSection('salon-cabelo')">Conheça Nossos Serviços</button>
      </div>
    </div>

    <!-- Seções de Serviços -->
    <div v-for="section in sections" :key="section.id" :id="section.id" class="salon-section">
      <h2 class="salon-section-title" :class="{ animate: animatedSections.includes(section.id) }">{{ section.title }}</h2>
      <div class="salon-services-grid">
        <div
            v-for="(service, index) in section.services"
            :key="index"
            class="salon-service-card salon-floating"
            :class="{ animate: animatedSections.includes(section.id) }"
            :style="{ transitionDelay: `${index * 0.1}s` }"
        >
          <img :src="service.image" class="salon-service-image">
          <div class="salon-service-icon">{{ service.icon }}</div>
          <h3>{{ service.name }}</h3>
          <div class="salon-service-duration">⏱️ {{ service.duration }}</div>
          <p>{{ service.description }}</p>
          <ul v-if="service.benefits" class="salon-benefits">
            <li v-for="(benefit, bIdx) in service.benefits" :key="bIdx">{{ benefit }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const sidebarOpen = ref(false);
const menuItems = [
  { id: 'salon-cabelo', label: 'Cabelo' },
  { id: 'salon-unhas', label: 'Unhas & Cílios' },
  { id: 'salon-sobrancelhas', label: 'Sobrancelhas' },
  { id: 'salon-facial', label: 'Facial' },
  { id: 'salon-corporal', label: 'Corporal' },
  { id: 'salon-depilacao', label: 'Depilação' },
  { id: 'salon-especiais', label: 'Especiais' },
];

const sections = [
  {
    id: 'salon-cabelo',
    title: '💇‍♀️ Cabelo & Tratamentos Capilares',
    services: [
      {
        name: 'Corte Personalizado',
        image: 'https://images.unsplash.com/photo-1562322140-8baeececf3df',
        icon: '✂️',
        duration: '40min',
        description: 'Transforme seu visual com cortes modernos e precisos. Inclui lavagem e secagem.',
      },
      {
        name: 'Mechas & Morena Iluminada',
        image: 'https://images.unsplash.com/photo-1600965965803-73d6f7658b96',
        icon: '🌞',
        duration: '4-6h',
        description: 'Técnica de luzimento estratégico para cabelos castanhos.',
        benefits: [
          'Ilumina o rosto sem danificar toda a estrutura capilar',
          'Efeito "férias na praia" com manutenção prática',
          'Baixo contraste para crescimento discreto das raízes',
        ],
      },
    ],
  },
  {
    id: 'salon-unhas',
    title: '💅 Unhas & Cílios',
    services: [
      {
        name: 'Manicure e Pedicure',
        image: 'https://images.unsplash.com/photo-1587502536263-9298f9f1903b',
        icon: '💅',
        duration: '1h',
        description: 'Cuidado completo com unhas das mãos e dos pés, com acabamento impecável.',
      },
      {
        name: 'Alongamento de Unhas em Gel',
        image: 'https://images.unsplash.com/photo-1620925481218-6b62e89f5122',
        icon: '💎',
        duration: '2h',
        description: 'Unhas mais longas e resistentes com aspecto natural.',
      },
      {
        name: 'Extensão de Cílios',
        image: 'https://images.unsplash.com/photo-1616486701049-1d9024c6c06d',
        icon: '👁️',
        duration: '1h30min',
        description: 'Volume e definição para os olhos com técnicas fio a fio ou volume russo.',
      },
    ],
  },
  {
    id: 'salon-sobrancelhas',
    title: '👁️‍🗨️ Sobrancelhas',
    services: [
      {
        name: 'Design de Sobrancelhas',
        image: 'https://images.unsplash.com/photo-1630055303521-694f0a03f2e0',
        icon: '🖌️',
        duration: '40min',
        description: 'Harmonização do olhar com técnicas de medição e simetria facial.',
      },
      {
        name: 'Henna',
        image: 'https://images.unsplash.com/photo-1588776814546-21831e7a3be4',
        icon: '🎨',
        duration: '30min',
        description: 'Preenchimento natural temporário com efeito de sombra nas sobrancelhas.',
      },
    ],
  },
  {
    id: 'salon-facial',
    title: '🌸 Estética Facial',
    services: [
      {
        name: 'Limpeza de Pele Profunda',
        image: 'https://images.unsplash.com/photo-1617339769364-7b4990ee3f6f',
        icon: '🧖‍♀️',
        duration: '1h30min',
        description: 'Remoção de impurezas, cravos e renovação celular com hidratação.',
      },
      {
        name: 'Peeling de Diamante',
        image: 'https://images.unsplash.com/photo-1594824476967-48c3b1f3d6e3',
        icon: '💎',
        duration: '50min',
        description: 'Esfoliação profunda que melhora textura e luminosidade da pele.',
      },
    ],
  },
  {
    id: 'salon-corporal',
    title: '🧘‍♀️ Estética Corporal',
    services: [
      {
        name: 'Massagem Relaxante',
        image: 'https://images.unsplash.com/photo-1612349317150-8df7de02aa39',
        icon: '💆‍♀️',
        duration: '1h',
        description: 'Alívio do estresse e dores musculares com toques suaves e aromaterapia.',
      },
      {
        name: 'Drenagem Linfática',
        image: 'https://images.unsplash.com/photo-1590080876823-3c8e4320f6c0',
        icon: '💧',
        duration: '1h',
        description: 'Redução de inchaços, retenção de líquidos e melhora da circulação.',
      },
    ],
  },
  {
    id: 'salon-depilacao',
    title: '🪒 Depilação',
    services: [
      {
        name: 'Depilação com Cera',
        image: 'https://images.unsplash.com/photo-1605478902912-8e87a6c4b823',
        icon: '🕯️',
        duration: '30min - 1h',
        description: 'Remoção eficaz dos pelos com menos agressão e mais durabilidade.',
      },
    ],
  },
  {
    id: 'salon-especiais',
    title: '💖 Procedimentos Especiais',
    services: [
      {
        name: 'Dia da Noiva',
        image: 'https://images.unsplash.com/photo-1583407730609-d3be0402c913',
        icon: '👰',
        duration: 'Pacote completo',
        description: 'Experiência completa de beleza para o grande dia. Cabelo, maquiagem, cuidados e muito mais.',
      },
    ],
  },
];

const animatedSections = ref([]);

const animateOnScroll = () => {
  sections.forEach(({ id }) => {
    const el = document.getElementById(id);
    if (el && el.getBoundingClientRect().top < window.innerHeight - 150 && !animatedSections.value.includes(id)) {
      animatedSections.value.push(id);
    }
  });
};

const scrollToSection = (id) => {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  sidebarOpen.value = false;
};

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value;
};

onMounted(() => {
  window.addEventListener('scroll', animateOnScroll);
  animateOnScroll();
});
</script>

<style scoped>
/*serviços*/
.salon-container * {
  margin: 0 !important;
  padding: 0 !important;
  box-sizing: border-box !important;
}

.salon-container {
  font-family: 'Arial', sans-serif !important;
  line-height: 1.6 !important;
  color: #333 !important;
  overflow-x: hidden !important;
  background: #f8f9fa !important;
  margin-left: 120px !important; /* Espaço para o menu lateral */
  padding-right: 20px !important;
}

/* Menu Lateral Flutuante */
.salon-sidebar {
  position: fixed !important;
  left: 20px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  z-index: 1000 !important;
  background: rgba(0, 0, 0, 0.9) !important;
  backdrop-filter: blur(15px) !important;
  border-radius: 25px !important;
  padding: 2rem 1rem !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3) !important;
  border: 1px solid rgba(255, 64, 129, 0.2) !important;
  transition: all 0.3s ease !important;
}

.salon-sidebar:hover {
  background: rgba(0, 0, 0, 0.95) !important;
  box-shadow: 0 25px 80px rgba(255, 64, 129, 0.2) !important;
}

.salon-logo {
  font-size: 1.5rem !important;
  font-weight: bold !important;
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
  text-align: center !important;
  margin-bottom: 2rem !important;
  writing-mode: vertical-rl !important;
  text-orientation: mixed !important;
}

.salon-nav-menu {
  list-style: none !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 1rem !important;
  align-items: center !important;
}

.salon-nav-menu li {
  width: 100% !important;
}

.salon-nav-menu a {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-decoration: none !important;
  color: white !important;
  font-weight: 500 !important;
  transition: all 0.3s ease !important;
  padding: 1rem !important;
  border-radius: 15px !important;
  font-size: 0.9rem !important;
  text-align: center !important;
  min-height: 50px !important;
  position: relative !important;
  overflow: hidden !important;
}

.salon-nav-menu a::before {
  content: '' !important;
  position: absolute !important;
  top: 0 !important;
  left: -100% !important;
  width: 100% !important;
  height: 100% !important;
  background: linear-gradient(90deg, transparent, rgba(255, 64, 129, 0.3), transparent) !important;
  transition: left 0.5s ease !important;
}

.salon-nav-menu a:hover {
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
  color: white !important;
  transform: translateX(5px) !important;
  box-shadow: 0 5px 20px rgba(255, 64, 129, 0.4) !important;
  text-decoration: none !important;
}

.salon-nav-menu a:hover::before {
  left: 100% !important;
}

/* Header simplificado apenas para o logo principal */
.salon-header {
  position: sticky !important;
  top: 0 !important;
  width: 100% !important;
  background: rgba(0, 0, 0, 0.95) !important;
  backdrop-filter: blur(10px) !important;
  z-index: 999 !important;
  padding: 1rem 0 !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 2px 20px rgba(0,0,0,0.3) !important;
  margin-bottom: 2rem !important;
  display: none !important; /* Esconder header, usar apenas sidebar */
}

/* Hero Section */
.salon-hero {
  background: linear-gradient(135deg, #000000 0%, #333333 100%) !important;
  padding: 80px 20px !important;
  text-align: center !important;
  color: white !important;
  margin-bottom: 3rem !important;
  border-radius: 20px !important;
  position: relative !important;
  overflow: hidden !important;
}

.salon-hero::before {
  content: '' !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  background: linear-gradient(45deg, rgba(255, 64, 129, 0.1) 0%, rgba(233, 30, 99, 0.1) 100%) !important;
  z-index: 1 !important;
}

.salon-hero-content {
  max-width: 800px !important;
  margin: 0 auto !important;
  position: relative !important;
  z-index: 2 !important;
}

.salon-hero h1 {
  font-size: 3rem !important;
  margin-bottom: 1rem !important;
  animation: fadeInUp 1s ease forwards !important;
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
}

.salon-hero p {
  font-size: 1.3rem !important;
  margin-bottom: 2rem !important;
  animation: fadeInUp 1s ease 0.3s forwards !important;
}

.salon-cta-button {
  display: inline-block !important;
  padding: 15px 40px !important;
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
  color: white !important;
  text-decoration: none !important;
  border-radius: 50px !important;
  font-weight: bold !important;
  transition: all 0.3s ease !important;
  animation: fadeInUp 1s ease 0.6s forwards !important;
  box-shadow: 0 10px 30px rgba(255, 64, 129, 0.4) !important;
}

.salon-cta-button:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 15px 40px rgba(255, 64, 129, 0.6) !important;
  color: white !important;
  text-decoration: none !important;
}

/* Seções de Serviços */
.salon-section {
  padding: 60px 20px !important;
  margin-bottom: 2rem !important;
  border-radius: 20px !important;
  position: relative !important;
  background: white !important;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1) !important;
}

.salon-section-title {
  text-align: center !important;
  font-size: 2.5rem !important;
  margin-bottom: 3rem !important;
  color: #333 !important;
  opacity: 0 !important;
  transform: translateY(30px) !important;
  transition: all 0.6s ease !important;
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
}

.salon-section-title.animate {
  opacity: 1 !important;
  transform: translateY(0) !important;
}

.salon-services-grid {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)) !important;
  gap: 2rem !important;
  max-width: 1200px !important;
  margin: 0 auto !important;
}

.salon-service-card {
  background: white !important;
  border-radius: 20px !important;
  padding: 2rem !important;
  border: 2px solid #f5f5f5 !important;
  transition: all 0.4s ease !important;
  opacity: 0 !important;
  transform: translateY(50px) !important;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1) !important;
  position: relative !important;
  overflow: hidden !important;
}

.salon-service-card::before {
  content: '' !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  height: 4px !important;
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
}

.salon-service-card.animate {
  opacity: 1 !important;
  transform: translateY(0) !important;
}

.salon-service-card:hover {
  transform: translateY(-10px) !important;
  box-shadow: 0 20px 60px rgba(255, 64, 129, 0.2) !important;
  border-color: #ff4081 !important;
}

.salon-service-image {
  width: 100% !important;
  height: 200px !important;
  object-fit: cover !important;
  border-radius: 15px !important;
  margin-bottom: 1.5rem !important;
  transition: transform 0.3s ease !important;
}

.salon-service-card:hover .salon-service-image {
  transform: scale(1.05) !important;
}

.salon-service-icon {
  width: 60px !important;
  height: 60px !important;
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
  border-radius: 50% !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  margin-bottom: 1rem !important;
  font-size: 1.5rem !important;
  position: absolute !important;
  top: 1rem !important;
  right: 1rem !important;
  z-index: 2 !important;
}

.salon-service-card h3 {
  color: #333 !important;
  font-size: 1.5rem !important;
  margin-bottom: 1rem !important;
  font-weight: 600 !important;
}

.salon-service-card p {
  color: #666 !important;
  margin-bottom: 1rem !important;
  line-height: 1.6 !important;
}

.salon-service-duration {
  background: linear-gradient(45deg, #ff4081, #e91e63) !important;
  color: white !important;
  padding: 0.5rem 1rem !important;
  border-radius: 20px !important;
  font-size: 0.9rem !important;
  display: inline-block !important;
  margin-bottom: 1rem !important;
  font-weight: 500 !important;
}

.salon-benefits {
  list-style: none !important;
  margin: 1rem 0 !important;
}

.salon-benefits li {
  color: #666 !important;
  margin: 0.5rem 0 !important;
  padding-left: 1.5rem !important;
  position: relative !important;
}

.salon-benefits li::before {
  content: '✨' !important;
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  color: #ff4081 !important;
}

/* Remover backgrounds diferentes - usar apenas cards brancos */
.salon-cabelo, .salon-unhas, .salon-sobrancelhas, .salon-facial,
.salon-corporal, .salon-depilacao, .salon-especiais {
  background: white !important;
}

/* Animações */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.salon-floating {
  animation: float 3s ease-in-out infinite !important;
}

/* Mobile Responsivo */
@media (max-width: 768px) {
  .salon-container {
    margin-left: 0 !important;
    padding: 0 10px !important;
  }

  .salon-sidebar {
    position: fixed !important;
    left: -200px !important;
    top: 0 !important;
    transform: none !important;
    height: 100vh !important;
    width: 200px !important;
    border-radius: 0 !important;
    border-top-right-radius: 20px !important;
    border-bottom-right-radius: 20px !important;
    transition: left 0.3s ease !important;
    padding: 2rem 1rem !important;
  }

  .salon-sidebar.open {
    left: 0 !important;
  }

  .salon-menu-toggle {
    display: block !important;
    position: fixed !important;
    top: 20px !important;
    left: 20px !important;
    z-index: 1001 !important;
    background: linear-gradient(45deg, #ff4081, #e91e63) !important;
    border: none !important;
    border-radius: 50% !important;
    width: 50px !important;
    height: 50px !important;
    color: white !important;
    font-size: 1.2rem !important;
    cursor: pointer !important;
    box-shadow: 0 5px 20px rgba(255, 64, 129, 0.4) !important;
  }

  .salon-logo {
    writing-mode: horizontal-tb !important;
    text-orientation: mixed !important;
    font-size: 1.2rem !important;
  }

  .salon-hero h1 {
    font-size: 2rem !important;
  }

  .salon-hero p {
    font-size: 1rem !important;
  }

  .salon-section-title {
    font-size: 1.8rem !important;
  }

  .salon-services-grid {
    grid-template-columns: 1fr !important;
  }
}

.salon-menu-toggle {
  display: none !important;
}

</style>
