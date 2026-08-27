import newIconsData from '../../../data/new-icons-added.json';

const STYLE_OPTIONS = ['Outline', 'Filled', 'Duotone'] as const;
const SIZE_OPTIONS = ['24', '36', '50', '60'] as const;
const NEW_ICONS_COUNT = (newIconsData as string[]).length;

export { STYLE_OPTIONS, SIZE_OPTIONS, NEW_ICONS_COUNT };
