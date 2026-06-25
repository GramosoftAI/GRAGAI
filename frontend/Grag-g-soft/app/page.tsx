// import Image from "next/image";
// import HomePage from "./home/page";

// export default function Home() {
//   return (
    
//   );
// }
"use client"

import { signIn, signOut, useSession } from "next-auth/react"
import HomePage from "./home/page";

export default function Home() {
  const { data: session } = useSession()

  return (
    <div>
      <HomePage />
      {!session ? (
        // <button onClick={() => signIn("google")}>
        //   Connect Google Drive
        // </button>
        <>
        </>
      ) : (
        <>
          {/* <p>{session.user?.email}</p> */}

          {/* <button onClick={() => signOut()}>
            Logout
          </button> */}
        </>
      )}
    </div>
  )
}