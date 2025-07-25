<template>
  <div class="salon-container">
    <!-- Menu Lateral Flutuante -->
    <div class="salon-sidebar" :class="{ open: isMobileMenuOpen }">
      <div class="salon-logo">RED Beauty</div>
      <nav>
        <ul class="salon-nav-menu">
          <li v-for="section in menuSections" :key="section.id">
            <a @click="scrollToSection(section.id)" href="#">{{ section.name }}</a>
          </li>
        </ul>
      </nav>
    </div>

    <!-- Botão Menu Mobile -->
    <button class="salon-menu-toggle" @click="toggleMobileMenu">☰</button>

    <!-- Hero Section -->
    <div class="salon-hero">
      <div class="salon-hero-content">
        <h1>Transforme sua Beleza</h1>
        <p>Descubra nossos serviços exclusivos e viva uma experiência única de cuidado e bem-estar</p>
        <a @click="scrollToSection('salon-cabelo')" href="#" class="salon-cta-button">Conheça Nossos Serviços</a>
      </div>
    </div>

    <!-- Seções de Serviços -->
    <div
        v-for="section in serviceSections"
        :key="section.id"
        :id="section.id"
        class="salon-section"
        :class="section.class"
    >
      <h2 class="salon-section-title" :class="{ animate: visibleSections.includes(section.id) }">
        {{ section.icon }} {{ section.title }}
      </h2>
      <div class="salon-services-grid">
        <div
            v-for="(service, index) in section.services"
            :key="index"
            class="salon-service-card"
            :class="{ animate: visibleSections.includes(section.id), 'salon-floating': section.id === 'salon-cabelo' }"
            :style="{ transitionDelay: `${index * 0.1}s` }"
        >
          <img
              v-if="service.image"
              :src="service.image"
              :alt="service.title"
              class="salon-service-image"
          >
          <div class="salon-service-icon">{{ service.icon }}</div>
          <h3>{{ service.title }}</h3>
          <div class="salon-service-duration">⏱️ {{ service.duration }}</div>
          <p>{{ service.description }}</p>
          <ul v-if="service.benefits" class="salon-benefits">
            <li v-for="benefit in service.benefits" :key="benefit">{{ benefit }}</li>
          </ul>
          <p v-if="service.quote"><em>{{ service.quote }}</em></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// Estados reativos
const isMobileMenuOpen = ref(false)
const visibleSections = ref([])

// Menu de navegação
const menuSections = [
  { id: 'salon-cabelo', name: 'Cabelo' },
  { id: 'salon-unhas', name: 'Unhas & Cílios' },
  { id: 'salon-sobrancelhas', name: 'Sobrancelhas' },
  { id: 'salon-facial', name: 'Facial' },
  { id: 'salon-corporal', name: 'Corporal' },
  { id: 'salon-depilacao', name: 'Depilação' },
  { id: 'salon-especiais', name: 'Especiais' }
]

// Dados dos serviços
const serviceSections = [
  {
    id: 'salon-cabelo',
    class: 'salon-cabelo',
    icon: '💇‍♀️',
    title: 'Cabelo & Tratamentos Capilares',
    services: [
      {
        image: 'https://images.unsplash.com/photo-1562322140-8baeececf3df?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '✂️',
        title: 'Corte Personalizado',
        duration: 'Tempo médio: 40min',
        description: 'Transforme seu visual com cortes modernos e precisos, elaborados para valorizar seu formato de rosto e estilo de vida. Inclui lavagem e secagem.'
      },
      {
        image: 'https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '✨',
        title: 'Mechas & Morena Iluminada',
        duration: 'Tempo médio: 4-6 horas',
        description: 'Técnica de luzimento estratégico para cabelos castanhos, utilizando balayage ou baby lights para criar reflexos naturais sem contraste marcado.',
        benefits: [
          'Ilumina o rosto sem danificar toda a estrutura capilar',
          'Efeito "férias na praia" com manutenção prática',
          'Baixo contraste para crescimento discreto das raízes'
        ],
        quote: '"Seus fios ganham luz natural e movimento cinematográfico!"'
      },
      {
        image: 'https://images.unsplash.com/photo-1605497788044-5a32c7078486?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '💫',
        title: 'Progressiva & Alisamentos',
        duration: 'Tempo médio: 3h',
        description: 'Alise com saúde! Utilizamos fórmulas modernas (sem formol ou com baixo dano) que alinham os fios, reduzem volume e proporcionam brilho intenso, respeitando a integridade do seu cabelo.'
      }
    ]
  },
  {
    id: 'salon-unhas',
    class: 'salon-unhas',
    icon: '💅',
    title: 'Unhas & Cílios',
    services: [
      {
        image: 'https://images.unsplash.com/photo-1604654894610-df63bc536371?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '💅',
        title: 'Manicure & Pedicure Premium',
        duration: 'Tempo médio: 1h50min',
        description: 'Mãos e pés impecáveis! Corte, lixamento, tratamento de cutículas, hidratação, esfoliação e esmaltação (comum ou em gel) com higiene absoluta e produtos esterilizados em autoclave.'
      },
      {
        image: 'https://images.unsplash.com/photo-1610992015732-2199de8dce7e?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '💎',
        title: 'Extensão de Unhas',
        duration: 'Tempo médio: 2h30min',
        description: 'Unhas longas, resistentes e perfeitas! Alongamento personalizado com gel ou fibra para um visual elegante e duradouro.'
      },
      {
        image: 'https://images.unsplash.com/photo-1616683693504-3ea7e9ad6fec?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '👁️',
        title: 'Extensão de Cílios Fio a Fio',
        duration: 'Tempo médio: 2h-2h30min',
        description: 'Olhar impactante 24h por dia! Aplicação de fios sintéticos ou de seda cílio a cílio, com efeito natural ou dramático, sem necessidade de máscara de cílios.'
      }
    ]
  },
  {
    id: 'salon-sobrancelhas',
    class: 'salon-sobrancelhas',
    icon: '🎨',
    title: 'Sobrancelhas & Maquiagem',
    services: [
      {
        image: 'https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '✏️',
        title: 'Design de Sobrancelhas',
        duration: '20min simples / 40min com henna',
        description: 'Designer personalizado para valorizar seu olhar! Formato perfeito + cor intensa! Definimos seu arco ideal e preenchemos falhas com pigmentação temporária (henna). Usamos técnicas de cera & pinça.'
      },
      {
        image: 'https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '💄',
        title: 'Maquiagem Profissional & Penteados',
        duration: 'Makeup: 1h / Penteado: 1h30min',
        description: 'Brilhe em qualquer ocasião! Maquiagem e penteados elegantes (coques, ondas, tranças) personalizados para eventos, noivas ou dia a dia.'
      },
      {
        image: 'https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
        icon: '🖋️',
        title: 'Micro Pigmentação',
        duration: 'Tempo médio: 1h30min',
        description: 'Correção semipermanente! Técnica de micropigmentação para realçar lábios com efeito blush ou reconstruir sobrancelhas com traços naturais e simétricos.'
      }
    ]
  },
  {
    id: 'salon-facial',
    class: 'salon-facial',
    icon: '🌸',
    title: 'Estética Facial',
    services: [
      {
        icon: '🧴',
        title: 'Limpeza de Pele Profunda',
        duration: 'Tempo médio: 50min',
        description: 'Desintoxicação e renovação! Higienização profunda com extração de impurezas, esfoliação, máscaras e hidratação para pele radiante e livre de cravos.'
      },
      {
        icon: '🔬',
        title: 'Microagulhamento com Enzimas',
        duration: 'Tempo médio: 50min',
        description: 'Rejuvenescimento com precisão! Agulhas microscópicas estimulam colágeno, enquanto enzimas ou ativos personalizados clareiam manchas, reduzem poros e tratam acne.'
      },
      {
        icon: '✨',
        title: 'Dermaplaning',
        duration: 'Tempo médio: 45min',
        description: 'Pele lisa, radiante e renovada! Procedimento com lâmina cirúrgica que remove pelos finos e células mortas, proporcionando textura aveludada e brilho imediato.',
        benefits: [
          'Pele instantaneamente lisa',
          'Brilho imediato',
          'Melhor absorção de produtos (até 70%)',
          'Maquiagem impecável'
        ]
      },
      {
        icon: '💉',
        title: 'Preenchimento Facial',
        duration: 'Consulte durações',
        description: 'Contorno jovem e harmonioso! Aplicação de ácido hialurônico para suavizar rugas, definir ângulos e restaurar volume facial com resultados naturais.'
      }
    ]
  },
  {
    id: 'salon-corporal',
    class: 'salon-corporal',
    icon: '💪',
    title: 'Estética Corporal',
    services: [
      {
        icon: '🤲',
        title: 'Liberação Miofascial',
        duration: 'Consulte durações',
        description: 'Alívio de tensões profundas! Técnica manual que libera aderências musculares e fasciais, melhorando mobilidade, reduzindo dores e promovendo bem-estar.'
      },
      {
        icon: '🌿',
        title: 'Tratamentos Corporais Personalizados',
        duration: 'Varia conforme protocolo',
        description: 'Combate à celulite, flacidez e gordura localizada! Protocolos com enzimas personalizadas para melhores resultados corporais.'
      }
    ]
  },
  {
    id: 'salon-depilacao',
    class: 'salon-depilacao',
    icon: '🪒',
    title: 'Depilação',
    services: [
      {
        icon: '⚡',
        title: 'Depilação a Laser',
        duration: 'Varia por área',
        description: 'Fim dos pelos indesejados! Tecnologia avançada para depilação definitiva facial, corporal e capilar. Sessões seguras, rápidas e eficazes para todos os fototipos.'
      },
      {
        icon: '🕯️',
        title: 'Depilação com Cera',
        duration: 'Varia por área',
        description: 'Pele lisa e duradoura! Remoção de pelos com cera de alta aderência em axilas, pernas, virilha e outras áreas, seguida de hidratação calmante.'
      }
    ]
  },
  {
    id: 'salon-especiais',
    class: 'salon-especiais',
    icon: '⭐',
    title: 'Tratamentos Especiais',
    services: [
      {
        icon: '🔆',
        title: 'Lavieen Laser Multifuncional',
        duration: 'Varia por área',
        description: 'Solução multifuncional! Tratamento com laser versátil para:',
        benefits: [
          'Facial: Clareamento de manchas, rejuvenescimento e tratamento de acne',
          'Capilar: Combate à queda de cabelo e estímulo de crescimento',
          'Corporal: Manchas, foliculite, clareamento, combate à flacidez'
        ]
      },
      {
        icon: '🎯',
        title: 'Despigmentação de Micropigmentação',
        duration: 'Varia conforme caso',
        description: 'Correção de procedimentos antigos! Remoção segura de pigmentos indesejados em sobrancelhas ou lábios com tecnologia a laser.'
      }
    ]
  }
]

// Métodos
const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

const scrollToSection = (sectionId) => {
  const element = document.getElementById(sectionId)
  if (element) {
    element.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
  }
  // Fechar menu mobile após clicar
  if (window.innerWidth <= 768) {
    isMobileMenuOpen.value = false
  }
}

const animateOnScroll = () => {
  const elements = document.querySelectorAll('.salon-section-title, .salon-service-card')

  elements.forEach(element => {
    const elementTop = element.getBoundingClientRect().top
    const elementVisible = 150

    if (elementTop < window.innerHeight - elementVisible) {
      element.classList.add('animate')

      // Adicionar seção à lista de visíveis
      const section = element.closest('.salon-section')
      if (section && !visibleSections.value.includes(section.id)) {
        visibleSections.value.push(section.id)
      }
    }
  })
}

const handleClickOutside = (event) => {
  const sidebar = document.querySelector('.salon-sidebar')
  const menuToggle = document.querySelector('.salon-menu-toggle')

  if (window.innerWidth <= 768 &&
      !sidebar?.contains(event.target) &&
      !menuToggle?.contains(event.target)) {
    isMobileMenuOpen.value = false
  }
}

// Lifecycle hooks
onMounted(() => {
  window.addEventListener('scroll', animateOnScroll)
  document.addEventListener('click', handleClickOutside)
  animateOnScroll() // Executar uma vez ao montar
})

onUnmounted(() => {
  window.removeEventListener('scroll', animateOnScroll)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.salon-container * {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.salon-container {
  font-family: 'Arial', sans-serif;
  line-height: 1.6;
  color: #333;
  overflow-x: hidden;
  background: #f8f9fa;
  margin-left: 120px;
  padding-right: 20px;
}

/* Menu Lateral Flutuante */
.salon-sidebar {
  position: fixed;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1000;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(15px);
  border-radius: 25px;
  padding: 2rem 1rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 64, 129, 0.2);
  transition: all 0.3s ease;
}

.salon-sidebar:hover {
  background: rgba(0, 0, 0, 0.95);
  box-shadow: 0 25px 80px rgba(255, 64, 129, 0.2);
}

.salon-logo {
  font-size: 1.5rem;
  font-weight: bold;
  background: linear-gradient(45deg, #ff4081, #e91e63);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-align: center;
  margin-bottom: 2rem;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.salon-nav-menu {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
}

.salon-nav-menu li {
  width: 100%;
}

.salon-nav-menu a {
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  color: white;
  font-weight: 500;
  transition: all 0.3s ease;
  padding: 1rem;
  border-radius: 15px;
  font-size: 0.9rem;
  text-align: center;
  min-height: 50px;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.salon-nav-menu a::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 64, 129, 0.3), transparent);
  transition: left 0.5s ease;
}

.salon-nav-menu a:hover {
  background: linear-gradient(45deg, #ff4081, #e91e63);
  color: white;
  transform: translateX(5px);
  box-shadow: 0 5px 20px rgba(255, 64, 129, 0.4);
}

.salon-nav-menu a:hover::before {
  left: 100%;
}

.salon-menu-toggle {
  display: none;
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 1001;
  background: linear-gradient(45deg, #ff4081, #e91e63);
  border: none;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  box-shadow: 0 5px 20px rgba(255, 64, 129, 0.4);
}

/* Hero Section */
.salon-hero {
  background: linear-gradient(135deg, #000000 0%, #333333 100%);
  padding: 80px 20px;
  text-align: center;
  color: white;
  margin-bottom: 3rem;
  border-radius: 20px;
  position: relative;
  overflow: hidden;
}

.salon-hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, rgba(255, 64, 129, 0.1) 0%, rgba(233, 30, 99, 0.1) 100%);
  z-index: 1;
}

.salon-hero-content {
  max-width: 800px;
  margin: 0 auto;
  position: relative;
  z-index: 2;
}

.salon-hero h1 {
  font-size: 3rem;
  margin-bottom: 1rem;
  animation: fadeInUp 1s ease forwards;
  background: linear-gradient(45deg, #ff4081, #e91e63);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.salon-hero p {
  font-size: 1.3rem;
  margin-bottom: 2rem;
  animation: fadeInUp 1s ease 0.3s forwards;
}

.salon-cta-button {
  display: inline-block;
  padding: 15px 40px;
  background: linear-gradient(45deg, #ff4081, #e91e63);
  color: white;
  text-decoration: none;
  border-radius: 50px;
  font-weight: bold;
  transition: all 0.3s ease;
  animation: fadeInUp 1s ease 0.6s forwards;
  box-shadow: 0 10px 30px rgba(255, 64, 129, 0.4);
  cursor: pointer;
}

.salon-cta-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 15px 40px rgba(255, 64, 129, 0.6);
  color: white;
  text-decoration: none;
}

/* Seções de Serviços */
.salon-section {
  padding: 60px 20px;
  margin-bottom: 2rem;
  border-radius: 20px;
  position: relative;
  background: white;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}

.salon-section-title {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 3rem;
  color: #333;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease;
  background: linear-gradient(45deg, #ff4081, #e91e63);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.salon-section-title.animate {
  opacity: 1;
  transform: translateY(0);
}

.salon-services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.salon-service-card {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  border: 2px solid #f5f5f5;
  transition: all 0.4s ease;
  opacity: 0;
  transform: translateY(50px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: hidden;
}

.salon-service-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(45deg, #ff4081, #e91e63);
}

.salon-service-card.animate {
  opacity: 1;
  transform: translateY(0);
}

.salon-service-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 20px 60px rgba(255, 64, 129, 0.2);
  border-color: #ff4081;
}

.salon-service-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 15px;
  margin-bottom: 1.5rem;
  transition: transform 0.3s ease;
}

.salon-service-card:hover .salon-service-image {
  transform: scale(1.05);
}

.salon-service-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(45deg, #ff4081, #e91e63);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  font-size: 1.5rem;
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 2;
}

.salon-service-card h3 {
  color: #333;
  font-size: 1.5rem;
  margin-bottom: 1rem;
  font-weight: 600;
}

.salon-service-card p {
  color: #666;
  margin-bottom: 1rem;
  line-height: 1.6;
}

.salon-service-duration {
  background: linear-gradient(45deg, #ff4081, #e91e63);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  display: inline-block;
  margin-bottom: 1rem;
  font-weight: 500;
}

.salon-benefits {
  list-style: none;
  margin: 1rem 0;
}

.salon-benefits li {
  color: #666;
  margin: 0.5rem 0;
  padding-left: 1.5rem;
  position: relative;
}

.salon-benefits li::before {
  content: '✨';
  position: absolute;
  left: 0;
  top: 0;
  color: #ff4081;
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
  animation: float 3s ease-in-out infinite;
}

/* Mobile Responsivo */
@media (max-width: 768px) {
  .salon-container {
    margin-left: 0;
    padding: 0 10px;
  }

  .salon-sidebar {
    position: fixed;
    left: -200px;
    top: 0;
    transform: none;
    height: 100vh;
    width: 200px;
    border-radius: 0;
    border-top-right-radius: 20px;
    border-bottom-right-radius: 20px;
    transition: left 0.3s ease;
    padding: 2rem 1rem;
  }

  .salon-sidebar.open {
    left: 0;
  }

  .salon-menu-toggle {
    display: block;
  }

  .salon-logo {
    writing-mode: horizontal-tb;
    text-orientation: mixed;
    font-size: 1.2rem;
  }

  .salon-hero h1 {
    font-size: 2rem;
  }

  .salon-hero p {
    font-size: 1rem;
  }

  .salon-section-title {
    font-size: 1.8rem;
  }

  .salon-services-grid {
    grid-template-columns: 1fr;
  }
}
</style>