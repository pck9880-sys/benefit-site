// 예전 주소(*.pages.dev)와 www 로 들어오면 대표 도메인으로 301 이동
const MAIN = "benefy.kr";
export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  if (url.hostname.endsWith(".pages.dev") || url.hostname === "www." + MAIN) {
    url.hostname = MAIN;
    url.protocol = "https:";
    url.port = "";
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
