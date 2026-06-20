// Source label chip for YouTube / Bilibili, matching the bot's source_label().
import { YouTubeIcon, BilibiliIcon, MusicIcon } from "./icons.jsx";

const SOURCE_META = {
  YouTube: { tone: "youtube", Icon: YouTubeIcon },
  Bilibili: { tone: "bilibili", Icon: BilibiliIcon },
};

export default function SourceBadge({ source }) {
  const meta = SOURCE_META[source] ?? { tone: "neutral", Icon: MusicIcon };
  const { Icon } = meta;
  return (
    <span className={`source source--${meta.tone}`}>
      <Icon />
      {source}
    </span>
  );
}
