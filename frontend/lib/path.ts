export const getBasePath = () => {
  return process.env.NEXT_PUBLIC_RUNTIME_BASE_PATH || '';
};

export const withBasePath = (path: string): string => {
  const basePath = getBasePath();
  if (!basePath) return path;

  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${basePath}${normalizedPath}`;
};

export const stripBasePath = (path: string): string => {
  const basePath = getBasePath();
  if (!basePath) return path;

  if (path.startsWith(basePath)) {
    return path.slice(basePath.length) || '/';
  }
  return path;
};
