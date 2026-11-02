import "./PhoneFrame.css";

export default function PhoneFrame({ children }) {
  return (
    <div className="phone-stage">
      <div className="phone-glow" aria-hidden="true" />
      <div className="phone-shell">
        <div className="phone-notch" aria-hidden="true" />
        <div className="phone-screen">{children}</div>
      </div>
    </div>
  );
}
