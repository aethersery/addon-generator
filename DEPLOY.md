# 🚀 Addon Generator - Deploy em 5 Minutos

> **Resultado:** Seu app em `https://seu-app.vercel.app` + API em `https://sua-api.railway.app`

---

## 📋 Pré-requisitos (uma vez só)

| Conta | Link | Grátis? |
|-------|------|---------|
| GitHub | [github.com](https://github.com) | ✅ |
| Railway | [railway.app](https://railway.app) | ✅ 500h/mês |
| Vercel | [vercel.com](https://vercel.com) | ✅ Ilimitado |
| Groq | [console.groq.com/keys](https://console.groq.com/keys) | ✅ 14.4k req/dia |
| OpenRouter | [openrouter.ai/keys](https://openrouter.ai/keys) | ✅ Créditos/dia |

---

## 🎯 PASSO 1: Suba para o GitHub

```bash
# No seu PC ou Termux:
cd addon-generator  # pasta raiz do projeto

git init
git add .
git commit -m "Addon Generator - Ready for deploy"

# Crie repo no GitHub (site) → "New repository" → nome: addon-generator
git remote add origin https://github.com/SEU_USUARIO/addon-generator.git
git branch -M main
git push -u origin main
```

---

## 🎯 PASSO 2: Deploy Backend no Railway

### 2.1 Crie o projeto
1. Acesse [railway.app](https://railway.app) → Login com GitHub
2. **"New Project"** → **"Deploy from GitHub repo"**
3. Selecione seu repo `addon-generator`
4. **Root Directory:** `addon-api` ⚠️ **IMPORTANTE**
5. Clique **"Deploy Now"**

### 2.2 Adicione PostgreSQL + Redis (grátis)
No painel do projeto Railway:
1. **"+ New"** → **Database** → **Add PostgreSQL**
2. **"+ New"** → **Database** → **Add Redis**
3. Railway cria automaticamente: `DATABASE_URL` e `REDIS_URL`

### 2.3 Configure Variáveis de Ambiente
Vá em **Variables** → **"+ New Variable"** → adicione:

| Nome | Valor | Obrigatório? |
|------|-------|--------------|
| `GROQ_API_KEY` | `gsk_...` (de console.groq.com/keys) | ✅ **SIM** |
| `OPENROUTER_API_KEY` | `sk-or-...` (de openrouter.ai/keys) | ✅ **SIM** |
| `TOGETHER_API_KEY` | (opcional) | ❌ |
| `GOOGLE_API_KEY` | (opcional) | ❌ |
| `ENABLE_TOGETHER` | `false` | ❌ |
| `ENABLE_GOOGLE` | `false` | ❌ |
| `ENABLE_OPENAI` | `false` | ❌ |
| `ENABLE_ANTHROPIC` | `false` | ❌ |
| `ENABLE_DEEPSEEK` | `false` | ❌ |
| `ENABLE_OLLAMA` | `false` | ❌ |

> As variáveis `DATABASE_URL` e `REDIS_URL` já existem (criadas pelo PostgreSQL/Redis).

### 2.4 Pegue a URL do Backend
Após deploy (verde ✅):
1. Clique no serviço `addon-api`
2. Copie a **Public URL** (ex: `https://addon-api-production-xxxx.up.railway.app`)
3. Teste: `https://SUA_URL/health` → deve retornar JSON

---

## 🎯 PASSO 3: Deploy Frontend no Vercel

### 3.1 Importe o projeto
1. Acesse [vercel.com](https://vercel.com) → Login com GitHub
2. **"Add New..."** → **"Project"**
3. Selecione repo `addon-generator`
4. **Root Directory:** `addon-generator` ⚠️ **IMPORTANTE**
5. Framework: **Next.js** (auto-detecta)

### 3.2 Configure Variável de Ambiente
Antes de clicar Deploy, vá em **Environment Variables**:

| Nome | Valor |
|------|-------|
| `NEXT_PUBLIC_API_URL` | `https://SUA_URL_RAILWAY` (do Passo 2.4) |

### 3.3 Deploy
Clique **"Deploy"** → aguarde ~2 min → ✅

### 3.4 Pegue a URL do Frontend
Ex: `https://addon-generator-xyz.vercel.app`

---

## 🎯 PASSO 4: Conecte Frontend → Backend (CORS)

No **Railway** (backend), vá em **Variables** → adicione:

| Nome | Valor |
|------|-------|
| `CORS_ORIGINS` | `https://SEU_FRONTEND.vercel.app,http://localhost:3000` |

> Redeploy automático no Railway após adicionar.

---

## 🎯 PASSO 5: Teste no Celular

```
1. Abra: https://SEU_FRONTEND.vercel.app no Chrome
2. Menu (⋮) → "Instalar app" / "Adicionar à tela inicial"
3. Abre o ícone no launcher
4. Digite tema: "Shadow Slave addon completo"
5. Clique "Gerar Addon Completo"
6. Baixa .mcaddon → toca → Minecraft importa → JOGA
```

---

## 🔧 Troubleshooting

| Problema | Solução |
|----------|---------|
| Build falha no Vercel | Verifique `NEXT_PUBLIC_API_URL` correta |
| API retorna 500 | Veja logs no Railway → "View Logs" |
| CORS error | `CORS_ORIGINS` no Railway deve ter URL do Vercel |
| Keys não funcionam | Teste em `https://SUA_API/health` e `/providers` |
| Build demora | Railway free: 500h/mês; Vercel: ilimitado |

---

## 📱 URLs Finais (guarde)

```
🎮 SEU APP (Frontend):  https://SEU_PROJETO.vercel.app
🔧 SUA API (Backend):   https://SEU_PROJETO.up.railway.app
📚 API Docs:            https://SEU_PROJETO.up.railway.app/docs
📊 Logs API:            Railway Dashboard → addon-api → Logs
📊 Logs Frontend:       Vercel Dashboard → Functions → Logs
```

---

## 💰 Custos (Free Tier)

| Serviço | Limite Grátis | Suficiente? |
|---------|---------------|-------------|
| Railway | 500h/mês CPU, 1GB RAM | ✅ ~200 gerações/mês |
| Vercel | 100GB bandwidth, builds ilimitados | ✅ |
| Groq | 14.4k req/dia, 30 RPM | ✅ |
| OpenRouter | Créditos diários (~50 req) | ✅ |
| PostgreSQL (Railway) | 1GB | ✅ |
| Redis (Railway) | 100MB | ✅ |

---

## 🆘 Precisa de ajuda?

1. **Logs Railway:** Dashboard → addon-api → "View Logs"
2. **Logs Vercel:** Dashboard → Functions → "View Logs"
3. **Teste API direto:** `curl https://SUA_API/health`
4. **Teste providers:** `curl https://SUA_API/providers`

---

## ✅ Checklist Final

- [ ] Repo no GitHub com código
- [ ] Railway: PostgreSQL + Redis criados
- [ ] Railway: `GROQ_API_KEY` + `OPENROUTER_API_KEY` configuradas
- [ ] Railway: `CORS_ORIGINS` com URL do Vercel
- [ ] Vercel: `NEXT_PUBLIC_API_URL` com URL do Railway
- [ ] Ambos deployados (verde ✅)
- [ ] Teste no celular: abre, instala, gera, baixa, joga

---

**🎉 Pronto! Seu gerador de addons profissional rodando 24/7 grátis.**
