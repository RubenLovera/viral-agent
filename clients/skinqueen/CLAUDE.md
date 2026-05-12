# SkinQueen — Contexto Completo del Cliente

**Cliente activo de TVA** | Contacto principal: Joe Fleming (CEO) + Gary  
**Tipo de contrato:** Pilot month (1 mes) → validar → Phase 2  
**Firmado:** Pendiente de firma de contrato para arrancar

---

## 1. El Producto

**Nombre oficial:** SkinQueens (también escrito SkinQueen)  
**Empresa desarrolladora:** NoLemon NoMelon Inc.  
**Plataformas:** iOS + Android  
**Tagline:** *"Stop guessing. Start matching."*  
**Posicionamiento:** "The smart filter between TikTok trends and what your skin actually needs."

### Qué hace la app

App de skincare personalizado que analiza videos de redes sociales y le dice al usuario si los productos mencionados son buenos o malos para **su piel específica**, según un perfil llamado **Skin DNA**.

**Flujo core (Share Mechanic — el diferenciador #1):**
1. Usuario ve video de skincare en TikTok/Instagram/Facebook
2. Comparte el video a SkinQueens con un tap (share sheet nativo iOS/Android)
3. La app extrae cada producto del video, analiza ingredientes y los cruza contra el Skin DNA del usuario
4. Notificación push: "3 productos encontrados. 2 hacen match con tu piel."

**Lo que SkinQueen NO hace:**
- No scanner de selfies / cámara
- No scanner de barcodes
- No diario/journal de piel
- No red social (sin feeds de amigos ni DMs)
- No servicio médico (siempre informacional, nunca reemplaza dermatólogo)
- No catálogo de productos para browsear

---

## 2. Features de la App

### Skin DNA Quiz (22 preguntas, ~2 minutos)
El corazón de todo. Captura:
- Tipo de piel, tono (10-shade picker), rango de edad
- Top 3 preocupaciones (acné, manchas, líneas finas, poros, textura, rojez, etc.)
- Nivel de sensibilidad + reacciones conocidas a ingredientes
- Zip code → clima local (UV, humedad, contaminación)
- Embarazo/lactancia → flags automáticos de ingredientes inseguros
- Medicamentos (tretinoin, Accutane, antibióticos tópicos)
- Mapa facial visual (zonas grasas / zonas con breakouts)
- Metas, presupuesto por producto, retailers preferidos (Sephora, Ulta, Amazon, Target, TikTok Shop, Dermstore)

Resultado: asignación de **Skin Archetype** + perfil completo.

### Los 9 Skin Archetypes
| Archetype | One-Liner | Piel |
|-----------|-----------|------|
| Glow Seeker | "Chasing radiance, one layer at a time." | Mixta, busca hidratación y brillo |
| Barrier Builder | "Calm skin is happy skin." | Sensible, rojez, foco en barrera |
| Acne Fighter | "Clear days ahead." | Grasa, propensa a breakouts |
| Age Defier | "Aging gracefully, one peptide at a time." | Anti-aging, retinoides y péptidos |
| Texture Refiner | "Smooth operator." | Poros visibles, textura irregular |
| Dark Spot Warrior | "Even tone, even glow." | Hiperpigmentación |
| Moisture Maven | "Hydration is my love language." | Muy seca, ceramidas y aceites |
| Skin Minimalist | "Less is more, and it shows." | Normal, rutina básica |
| Skin Explorer | "Your skin, your rules." | Perfil único, fallback archetype |

Los archetypes están diseñados para **ser compartibles** — link público a Skin DNA (`skinqueens.com/skin-dna/abc123`).

### Match Tiers (sistema de compatibilidad)
- **Gold (80-100%):** fondo `#FFF8F0`, texto `#D4A574`, ícono 👑
- **Rose (50-79%):** fondo `#FFF0F5`, texto `#E8A0B4`
- **Stone (<50%):** fondo `#F5F0EB`, texto `#4A4A68`

### Dupe Finder
Encuentra alternativas más baratas para productos caros con los mismos activos.

### Routine Grader
Usuario ingresa hasta 10 productos (AM/PM). La AI corre:
- Conflict detection
- Gap analysis
- Sinergias
- Score general
- "Better Match" (producto más compatible) + "Better Value" (alternativa más barata)

### Personalized Feed
Cards de productos con % de match. Filtros por preocupación, tipo, score mínimo, creador.

---

## 3. Modelo de Negocio

| Plan | Precio | Trial |
|------|--------|-------|
| Annual (free trial) | ~$59.99/año | 7 días gratis |
| Annual (paid trial) | ~$59.99/año | 30 días por ~$1.99 |
| Monthly | ~$9.99/mes | Sin trial |

Free: solo quiz + ver Skin DNA. Todo lo demás requiere suscripción.  
**Savings pitch:** $35/mes ahorrado vs $350+ desperdiciado sin SkinQueen.

---

## 4. Target Personas (prioridad de campaña)

| Persona | Edad | Dolor principal |
|---------|------|-----------------|
| **SkinTok Scroller** (primario, 30% de creadores) | 18-30 | Overwhelmed por consejos contradictorios, compra todo |
| **Busy Mom** (20%) | 28-40 | Sin tiempo para investigar, quiere respuestas rápidas |
| **Gen Z Student** (20%) | 16-22 | No puede gastar dinero en lo incorrecto |
| **Late-Twenties Professional** (15%) | 25-32 | Construyendo primera rutina seria |
| **Sensitive Skin Sufferer** (15%) | Cualquier edad | Miedo a reacciones, necesita chequeo de ingredientes |

---

## 5. Posicionamiento vs Competidores

**Competidores directos:** OnSkin, Lovi, SkinSort

| Dimensión | Competidores | SkinQueens |
|-----------|-------------|------------|
| Descubrimiento | Base de datos o barcode scanner | Share de video TikTok — productos del contenido que ya consumes |
| Personalización | Tipo de piel genérico | 22 factores incluyendo medicamentos, embarazo, clima, presupuesto |
| Esfuerzo | Buscar/escanear cada producto | Un tap desde TikTok → todos los productos del video |
| Ingredientes | Ratings genéricos | Personalizados por sensibilidad específica del usuario |
| Rutina | Básico o ninguno | Conflict detection, gap analysis, better-match y better-value |
| Social | Ninguno | Share sheet nativa iOS/Android dentro de TikTok/Instagram |

---

## 6. Estadísticas y Mensajes Clave

- **74%** de las recomendaciones de skincare en redes no consideran el tipo de piel
- **$350+** desperdiciados/año sin SkinQueen
- **$35/mes** en ahorro promedio con SkinQueen
- **22 preguntas**, ~2 minutos para el quiz
- **10K+ Happy Queens** (social proof)
- **4.8 Star Rating** (social proof)

**Taglines de la app:**
- "Stop guessing. Start matching."
- "The smart filter between TikTok trends and what your skin actually needs."
- "Social finds the trends. We find your match."
- "Your bathroom shouldn't be a graveyard."
- "Overwhelmed by SkinTok?"
- "What works for a TikTok creator might ruin your skin barrier."

**Reglas de claim para contenido UGC:**
- ✅ SAFE: "absorbed into the bloodstream," "linked to hormone changes," "the FDA has requested more safety data"
- ❌ AVOID: "causes cancer," "toxic," "poisons your body," "will make you infertile," promesas de resultados específicos de piel

---

## 7. Plan de Campaña TVA (Pilot Month)

**Contactos:** Joe Fleming (founder/CEO) + Gary  
**Duración:** 1 mes piloto desde la firma del contrato

### Deadlines
| Semana | Hito |
|--------|------|
| Week 1 | Creator sourcing, contratos firmados, briefs entregados, primeros 100+ videos live |
| Weeks 2-3 | Cadencia completa: ~125 videos/semana (UGC + AI) |
| Week 4 | Validar resultados + reporte final + plan Phase 2 |

### Estructura de cuentas y volumen
| Track | Volumen | Cuentas |
|-------|---------|---------|
| UGC (creadores reales) | ~500 videos/mes (~50/creador) | 10 TikTok accounts frescas |
| AI / Carousels | ~250-300 piezas/mes | 3-4 cuentas frescas |
| **Total** | **~750-800 piezas/mes** | **13-14 cuentas** |

### Mix de demografía de creadores
| Demo | % | Razón |
|------|---|-------|
| Skincare obsessives (18-25) | 30% | Core SkinTok, alto engagement |
| Busy moms (28-40) | 20% | Ángulo relatable, underserved |
| Gen Z students (16-22) | 20% | Ángulo budget, dupe finder |
| Late-twenties professionals | 15% | Aspiracional, primera rutina |
| Sensitive skin creators | 15% | Niche pero alta intención |

---

## 8. Hook Angles para UGC (priorizados)

### Tier 1 — Probar primero (mayor prioridad)

**1. Impulse Interception**
> "POV: I almost bought this $80 serum until I shared the video to SkinQueens"

Mecánica: creador mira video viral, lo comparte a la app, reacciona al veredicto.  
El screen-record del share flow ES el contenido.

**2. Waste / Drawer Audit**
> "My skincare drawer is $400 of products I never use. This app told me why."

Mecánica: creador muestra su cajón desordenado, escanea productos uno por uno, reacciona a los veredictos. Alta relabilidad — todos tienen este cajón.

**3. Product Conflict Reveal**
> "Three products in my routine were canceling each other out"

Mecánica: creador ingresa su rutina, la app muestra conflictos, reacción genuina de sorpresa. Educacional + impactante = alto save rate.

**4. Skin DNA Quiz Reveal**
> Creador hace el quiz en cámara, lee resultados en voz alta, reacciona a su perfil ("wait, my skin is actually THIS type?")

Mecánica: interactivo, personal, shareable.

### Tier 2 — Ángulos secundarios

**5. Anti-Influencer / Contrarian**
> "Stop buying skincare your favorite creator told you to buy"

Llama out al influencer-skincare-industrial complex. Posiciona SkinQueens como truth-teller.

**6. Dupe Finder / Value**
> "This app found a $14 dupe for the $80 thing I was about to buy"

Mostrar el exact match y comparación de precio en pantalla. Audiencia budget-conscious.

**7. Morning/Night Routine Integration**
Creador muestra su rutina, menciona que chequeó todo en SkinQueens primero. Sutil, lifestyle-integrated.

---

## 9. Reglas de Contenido (DO / DON'T)

### DO:
- Mostrar la app siendo USADA (no solo el ícono o splash screen)
- Filmar reacciones genuinas a resultados del quiz y veredictos de productos
- Usar el share-to-app flow como momento core del contenido
- Dejar que el producto se defienda solo a través del screen recording
- Incluir el nombre de la app visible en pantalla (para que viewers puedan buscarlo)

### DON'T:
- **NUNCA** poner CTA directo en el video (no "link in bio", no "download now")
- **NUNCA** scriptear la reacción (la sorpresa genuina convierte, la falsa no)
- **NUNCA** hacer claims médicos o dermatológicos
- **NUNCA** prometer resultados específicos de piel ("this will cure your acne")
- **NUNCA** mencionar competidores por nombre negativamente
- **NUNCA** usar estética sobre-producida/pulida (debe parecer contenido orgánico)

### Touch Points (en lugar de CTAs directos):
- Nombre de la app visible en pantalla durante el uso
- Descripción menciona la app naturalmente
- Bio link (si el creador tiene uno)
- Pinned comment con el nombre de la app
- Responder comments que preguntan "what app is this?"

---

## 10. Track AI / Carousels (paralelo al UGC)

Correr simultáneamente con el track UGC. 3-4 cuentas separadas. Formatos:
- Before/after skincare routine slideshows
- "$80 serum vs $14 dupe" comparison carousels
- Skin DNA quiz result infographics
- Product conflict breakdowns ("These 3 products cancel each other out")
- Ingredient spotlight carousels

**Estrategia:** AI content testa 30+ variantes de hooks por semana para encontrar winners rápido. Los hooks ganadores del track AI se alimentan a los briefs de UGC (y viceversa).

---

## 11. Métricas de Éxito

| Métrica | Target |
|---------|--------|
| Hook rate (1s retention) | >50% |
| View-through rate (3s) | >35% |
| Engagement rate | >3% |
| App Store conversion | >25% de viewers que visitan la página |
| Cost per view | <$0.03 |

---

## 12. Referencia de Contenido SkinTok

Formatos tendencia a estudiar y replicar:
- **Shelfie videos** — mostrar colección completa de skincare
- **GRWM (Get Ready With Me)** — rutinas completas
- "Products I regret buying" / "Products that changed my skin"
- **Ingredient call-out videos** — "If your moisturizer has THIS, throw it away"
- Dupes y alternativas

---

## 13. Inteligencia de Ingredientes (para briefs y coaching de creadores)

Esta sección es el material de fondo para crear contenido educativo de alta credibilidad. Basado en estudios clínicos y regulaciones FDA/EU.

### Villanos (para posicionar contra):

**Oxibenzona (Oxybenzone)** — el villano más fuerte
- FDA encontró que se absorbe al bloodstream 50-100x sobre el threshold de seguridad tras UN DÍA de uso
- Detectado en 85% de muestras de leche materna (estudio suizo 2008)
- Encontrado en 96%+ de adultos en vigilancia NHANES
- Baneado en Hawaii, Key West, Virgin Islands, Aruba, Palau
- Hook: *"The FDA tested sunscreen ingredients in human volunteers. After ONE day of use, oxybenzone was in their blood at concentrations 50 to 100 TIMES higher than the safety threshold. It's still in 2 out of 3 chemical sunscreens sold in the US."*

**Parabenos** (butyl- e isobutylparaben)
- Identificados como disruptores endocrinos (Danish Centre on Endocrine Disruptors)
- Detectados en casi 100% de muestras de orina de adultos
- Estudio HERMOSA: cambiar a productos sin parabenos redujo los biomarkers en 3 DÍAS
- Hook: *"Researchers took 100 teenage girls and switched them to paraben-free products for just 3 days. Their biomarker levels for these chemicals dropped by 27 to 44 percent. THREE DAYS."*

**Fragrance / Parfum** (el umbrella term)
- Por ley US, "fragrance" puede esconder miles de ingredientes no declarados
- La UE obliga a listar 26 alérgenos específicos; EEUU no tiene equivalente
- Dermatitis alérgica por contacto: afecta 1-3% de la población (1 de cada 30 personas)
- Hook: *"By US law, the word 'fragrance' on a label can hide up to thousands of undisclosed ingredients."*

**Aceites esenciales** — el "natural ≠ safe" angle
- Estudio 10 años, red alemana de dermatitis de contacto, 10.930 pacientes:
  - Ylang-ylang oil: 3.9% reacciones de patch test positivas
  - Lemongrass oil: 2.6%
  - Sandalwood oil: 1.8%
- Hook: *"'Natural' doesn't mean safe for skin. Ylang-ylang triggered allergic skin reactions in 3.9% of tested patients. That's nearly 1 in 25 people."*

### Combos que se cancela mutuamente (el "Conflict Reveal" angle):

| Combinación problemática | Por qué falla | Fix |
|--------------------------|---------------|-----|
| Retinol + AHAs/BHAs | Sobre-exfoliación → redness, daño de barrera, más breakouts | Alternar días o split AM/PM |
| Retinol + Benzoyl Peroxide | BPO oxida e inactiva el retinol; ambos son muy secantes | BPO mañana, retinol noche |
| Vitamina C + AHAs/BHAs | Disrumpe el ácido mantle, compromete la barrera | No combinar en misma sesión |
| Vitamina C + Benzoyl Peroxide | BPO oxida la vitamina C, neutralizando su función antioxidante | Sesiones separadas |

Hook: *"If you're using vitamin C and benzoyl peroxide in the same routine, the BPO is oxidizing your vitamin C the moment they touch. You're paying for a $60 serum that's been neutralized by your acne treatment."*

### Heroes (combos que SÍ funcionan, con ciencia):

| Goal | Combo héroe | Por qué funciona |
|------|------------|-----------------|
| Anti-aging | Vitamina C + E + Ferulic Acid | 8x protección UV. Estudio Duke 2005, replicado en múltiples ensayos clínicos |
| Anti-aging | Retinol + Hyaluronic Acid | Retinol estimula producción endógena de HA; HA hidrata desde afuera. Estudio Archives of Derm 2007 |
| Acné | Salicylic Acid + Niacinamide | Niacinamida sola igual de efectiva que clindamicina 1% para acné inflamatorio |
| Manchas | Tranexamic Acid + Kojic Acid + Niacinamide | 3 mecanismos anti-melanogénesis distintos; igualó o superó hidroquinona en estudios |
| Piel sensible | Ceramidas 3:1:1 + Niacinamide | Ceramidas reponen la barrera desde afuera; niacinamida activa producción propia de ceramidas |

Hook anti-aging: *"Vitamin C protects your skin from UV damage 4 times better than no product. Add vitamin E? Still 4 times. Now add ferulic acid — and protection DOUBLES to 8x. This combination has been in dermatology research since 2005."*

### Regla de oro del Marketing Playbook
> Estructura de cada ángulo: **Real evidence + named villain + accessible hero.** Nunca terminar en el problema — siempre ofrecer la solución en el mismo breath.

**5 reglas universales para claims de skincare:**
1. Lead con un número o nombre específico ("6 ingredients the FDA wants more safety data on")
2. Citar un regulador o estudio real (FDA, JAMA, EU Commission)
3. Nombrar el ingrediente villano (especificidad = credibilidad)
4. Dar la alternativa en el mismo breath
5. No overclaimar: "linked to," "associated with," "FDA wants more safety data" — nunca "causes cancer"

---

## 14. Perfil del Cliente: Joe Fleming (CEO)

**Empresa:** NoLemon NoMelon Inc. (aka "NoLemon")  
**Cargo:** CEO y Founder — se llama a sí mismo "Chief Lemon Slayer"  
**Ubicación:** San Francisco Bay Area  
**Background:** Finance (Crédit Agricole CIB, BFAM Partners en Hong Kong) → Tech startups  
**Educación:** University of Bristol (2014-2017)  
**LinkedIn tagline:** "No risk, no story."

**Su modelo de negocio:** Portfolio de apps AI-first para consumidores. Actualmente:
- **SkinQueens** — app de skincare IA (nuestro cliente)
- **BiteMate AI** — app de recomendación de comida con IA (lanzada marzo 2026, iOS + Android)

**Ángulo para conversaciones con Joe:**
- Tiene background dual: finance + founder B2C. Entiende de fondeo y de iterar al consumidor.
- **No es el founder de una sola app** — es constructor de un portfolio de productos AI. Hablar de sistemas para escalar y automatización resuena porque está tratando de escalar múltiples apps simultáneamente.
- Puedes comparar notas sobre retención de usuarios y uso de IA en ops.

---

## 15. Brand Voice y Design System (para activos propios)

**Voz:** "Tu amiga con un PhD" — cálida y cuidadosa ("Let's find something...") pero respaldada con ciencia ("skin barrier," "skin DNA").  
**Persona en segunda persona** — siempre "you/your," nunca "we."  
**La mascota Queenie** usa primera persona con emociones (✨ 🤔 😔).  
**La metáfora "Queen"** es load-bearing pero contenida — aparece en estados vacíos, loading, y "happy queens." Fuera de esos momentos, el tono es clínico y calmado.

**Paleta (para cualquier activo que creemos):**
- Fondo principal: `#FFFAF7` warm white
- Acento primario: `#D4A574` Crown Gold
- Rose: `#E8829A` / Blush: `#F8C8DC`
- Texto: `#1A1A1A` charcoal

**Tipografía:** Playfair Display (serif) para títulos de marca; system sans (SF Pro/Roboto) para UI.

**Casing de copy:**
- Títulos: Sentence case — "Stop guessing. Start matching."
- Labels: UPPERCASE con tracking — "SKIN DNA TEST"
- Botones: Title Case imperativo — "Start My Quiz"

---

## 16. Archivos de Referencia

Todos en `/Users/rubenlovera/Downloads/SkinQueen Data/`:
- `CONTENT BRIEF UGC - SkinQueens.docx` — brief oficial de la campaña
- `# SkinQueen — Complete Product & User Experience Brief.docx` — brief completo del producto
- `Perfil cliente - Joe Fleming.docx` — perfil del CEO
- `SkinQueens - UGC + AI - Ruben Lovera.docx` — propuesta/plan de Rubén
- `Skincare_IngredientResearch_Reference.pdf` — research de ingredientes (fuente científica)
- `Skincare_IngredientMarketing_Playbook.pdf` — playbook de marketing con hooks ready-to-shoot
- `SkinQueen Design System/` — sistema de diseño completo (assets, colores, tipografía, componentes React)
