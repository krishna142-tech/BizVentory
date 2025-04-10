export default async (request) => {
  return new Response("Hello from the edge!", {
    headers: { "content-type": "text/plain" },
  });
}; 