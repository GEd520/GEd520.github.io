export default {
  async fetch(r, env, ctx) {
    return handleRequest(r);
  },
};

async function handleRequest(request) {
  try {
    const headers = request.headers;
    const url = new URL(request.url);
    const repoOwner = url.searchParams.get('repoOwner');
    const repoName = url.searchParams.get('repoName');
    const path = url.searchParams.get('path') || '';
    const token = url.searchParams.get('token');

    if (!repoOwner || !repoName || !token) {
      return new Response(JSON.stringify({
        msg: 'Missing required parameters: repoOwner, repoName, or token',
        code: 400
      }), { status: 400 });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({
        msg: 'Invalid request method. Only POST is supported.',
        code: 405
      }), { status: 405 });
    }

    const formData = await request.formData();
    const file = formData.get('file');

    // 获取原始文件名
    const originalFileName = file.name;
    // 读取文件为ArrayBuffer
    const contentBuffer = await file.arrayBuffer();

    // 计算哈希
    const [sha, md5] = await calculateHash(contentBuffer);
    // 从原始文件名中提取扩展名
    const fileExtension = originalFileName.split('.').pop();
    const githubFileName = `${md5}.${fileExtension}`;

    // 构造路径
    const encodedPath = path
      .split('/')
      .filter(segment => segment)
      .map(segment => encodeURIComponent(segment))
      .join('/');

    const fullPath = encodedPath
      ? `${encodedPath}/${githubFileName}`
      : githubFileName;

    // GitHub API请求
    const githubUrl = `https://api.github.com/repos/${encodeURIComponent(repoOwner)}/${encodeURIComponent(repoName)}/contents/${fullPath}`;

    const githubRequest = new Request(githubUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `token ${token}`,
        'User-Agent': headers.get('user-agent'),
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github+json'
      },
      body: JSON.stringify({
        message: `Upload ${originalFileName}`,
        content: arrayBufferToBase64(contentBuffer),
        sha: sha,
        branch: 'main'
      })
    });

    const githubResponse = await fetch(githubRequest);
    return new Response(githubResponse.body, {
      status: githubResponse.status,
      statusText: githubResponse.statusText,
      headers: githubResponse.headers
    });
  } catch (e) {
    return new Response(JSON.stringify({
      msg: e.message,   // 显示更清晰的错误信息
      code: 500
    }), { status: 500 });
  }
}

// ArrayBuffer转Base64
function arrayBufferToBase64(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}

// 计算SHA1和MD5
async function calculateHash(contentBuffer) {
  const contentBytes = new Uint8Array(contentBuffer);

  // 构造Git Blob头部
  const header = `blob ${contentBytes.length}\0`;
  const encoder = new TextEncoder();
  const headerBytes = encoder.encode(header);

  // 合并头部和内容
  const totalBytes = new Uint8Array(headerBytes.length + contentBytes.length);
  totalBytes.set(headerBytes, 0);
  totalBytes.set(contentBytes, headerBytes.length);

  // 计算SHA-1
  const shaBuffer = await crypto.subtle.digest('SHA-1', totalBytes);
  const shaArray = Array.from(new Uint8Array(shaBuffer));
  const sha=shaArray.map(b => b.toString(16).padStart(2, '0')).join('')

  // 计算MD5
  const md5Buffer = await crypto.subtle.digest('MD5', contentBuffer);
  const md5Array = Array.from(new Uint8Array(md5Buffer));
  const md5 = md5Array.map(b => b.toString(16).padStart(2, '0')).join('');
  return [sha, md5];
}

// 上传时间 yyyyMMddHHmmss
function uploadTime() {
  const pad = n => n.toString().padStart(2, '0');
  const now = new Date();
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds())
  ].join('');
}