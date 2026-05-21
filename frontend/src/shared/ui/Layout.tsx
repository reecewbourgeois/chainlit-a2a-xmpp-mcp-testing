import styles from "./Layout.module.scss";

export function Flexbox(props: React.HTMLAttributes<HTMLDivElement>) {
  const { className, ...rest } = props;

  return <div className={`${styles.flexbox} ${className || ""}`} {...rest} />;
}

export function Grid(props: React.HTMLAttributes<HTMLDivElement>) {
  const { className, ...rest } = props;

  return <div className={`${styles.grid} ${className || ""}`} {...rest} />;
}
