// ========== 配置区 ==========
const ACCELERATE_DOMAIN = "github.your.workers.domain.com"; // 你的自定义加速域名
// =======================================

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  let targetUrl = url.href.replace(url.origin, 'https://github.com')

  // 适配 Raw/Gist/Git 资源
  if (url.pathname.startsWith('/raw/')) {
    targetUrl = url.href.replace(url.origin + '/raw', 'https://raw.githubusercontent.com')
  } else if (url.pathname.startsWith('/gist/')) {
    targetUrl = url.href.replace(url.origin + '/gist', 'https://gist.githubusercontent.com')
  } else if (url.pathname.startsWith('/gist-web/')) {
    targetUrl = url.href.replace(url.origin + '/gist-web', 'https://gist.github.com')
  }

  // 修复请求头，模拟正常访问
  const targetHost = new URL(targetUrl).host
  const newHeaders = new Headers(request.headers)
  newHeaders.set('Host', targetHost)
  newHeaders.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
  newHeaders.delete('CF-Connecting-IP')
  newHeaders.delete('CF-Ray')

  const newRequest = new Request(targetUrl, {
    method: request.method,
    headers: newHeaders,
    body: request.body,
    redirect: 'follow'
  })

  try {
    const response = await fetch(newRequest)
    // 构造新响应，添加自定义加速头
    const newResponse = new Response(response.body, response)
    
    // ========== 添加自定义 HTTP 头 ==========
    newResponse.headers.set('X-Accelerated-By', ACCELERATE_DOMAIN)
    newResponse.headers.set('X-Accelerator-Version', '1.0')
    // ==================================================
    
    newResponse.headers.set('Access-Control-Allow-Origin', '*')
    return newResponse
  } catch (e) {
    return new Response(`Worker 转发失败: ${e.message}`, { status: 502 })
  }
}