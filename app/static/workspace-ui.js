export function shouldShowDesignSidebar(workspace) {
  return workspace === 'design';
}

export function shouldShowMockupGuides(hasImage) {
  return !hasImage;
}

if (typeof window !== 'undefined') {
  window.WorkspaceUI = { shouldShowDesignSidebar, shouldShowMockupGuides };
}
